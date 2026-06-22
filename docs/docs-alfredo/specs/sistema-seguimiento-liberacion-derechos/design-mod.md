# Documento de Diseño Técnico

## Overview

Este documento presenta el diseño técnico de un sistema web multiusuario para el seguimiento del proceso de liberación de derechos de vía de proyectos ferroviarios que afectan propiedad social (ejidos y comunidades) en México. El sistema reemplaza el actual seguimiento basado en Excel, proporcionando gestión centralizada de datos, control de acceso basado en roles, tableros de control en tiempo real, visualización geográfica interactiva y capacidades completas de reporteo.

**Objetivos Principales:**
- Centralizar el seguimiento de liberación de derechos de vía en una base de datos relacional con capacidades geoespaciales
- Proporcionar acceso concurrente a múltiples usuarios con control basado en roles (incluyendo rol de Geógrafo para gestión cartográfica)
- Generar tableros y visualizaciones de progreso en tiempo real con mapas interactivos
- Calcular automáticamente superficies afectadas y liberadas mediante análisis geoespacial
- Visualizar el avance del proyecto en mapas con codificación de colores por estatus
- Mantener trazabilidad completa mediante auditoría de cambios
- Facilitar la migración desde hojas de cálculo Excel existentes
- Soportar importación y gestión de geometrías desde archivos geoespaciales estándar
- Soportar flujos de trabajo complejos incluyendo asambleas, convenios y procesos registrales

### Resumen Ejecutivo

El sistema gestiona el proceso legal y administrativo de liberación de derechos de vía para proyectos ferroviarios en México. Este proceso involucra:

**Entidades Territoriales:**
- **Tramos**: Segmentos principales del proyecto ferroviario con representación geométrica (líneas)
- **Frentes**: Subdivisiones de los tramos con geometrías lineales propias
- **Núcleos Agrarios**: Ejidos y comunidades (entidades de propiedad social) afectados por el proyecto, representados como polígonos georreferenciados

**Procesos Documentales:**
- **Sensibilización**: Reuniones de concientización con las comunidades
- **Caminamientos**: Inspecciones técnicas de campo
- **Asambleas**: Reuniones formales de ejidatarios/comuneros para aprobar convenios
- **Convenios**: Acuerdos legales de ocupación de terreno. Los tipos varían según el derecho afectado: para colectivos (COP, Modificatorio, Superficie Adicional, Obras Complementarias) y para individuales (COP, Modificatorio, Ampliación, Ampliación Remanente)
- **Inscripción RAN**: Proceso de registro en el Registro Agrario Nacional
- **FIFONAFE**: Proceso de pago de indemnizaciones a través del fideicomiso

**Análisis Geoespacial:**
- **Intersecciones Geométricas**: Cálculo automático de áreas afectadas mediante intersección de Frentes con Núcleos Agrarios
- **Transformación de Coordenadas**: Conversión entre WGS84 (visualización web) y UTM (documentos jurídicos)
- **Cálculo de Superficies**: Determinación automática de hectáreas y metros cuadrados afectados
- **Validación Topológica**: Verificación de geometrías válidas sin auto-intersecciones

**Actores del Sistema:**
- **Administradores**: Gestionan usuarios y configuración del sistema
- **Usuarios de Captura**: Registran y actualizan información del proceso
- **Geógrafos**: Capturan y editan geometrías de Tramos, Frentes y Núcleos Agrarios
- **Usuarios Visualizadores**: Consultan reportes, tableros de progreso y mapas interactivos

### Contexto del Dominio

#### Flujo de Proceso Integrado

El sistema sigue el proceso operativo descrito en `Descripción proceso.md`, el cual se estructura en 4 fases principales:

**Fase 1: Identificación Administrativa y Diagnóstico Legal**
- Captura de datos generales: Consecutivo, Entidad/Municipio, Residencia, Núcleo Agrario, E/C, Tramo
- Control de ORV (Órganos de Representación y Vigilancia): Verificación de vigencia de autoridades
- Control de Padrón: Número de ejidatarios/comuneros para cálculo de quórum
- Documentación soporte y excepciones (Comunidad Indígena, Expropiación Directa)

**Fase 2: Acercamiento en Campo**
- **Sensibilización**: Reuniones informativas con el núcleo agrario
- **Caminamiento**: Inspecciones técnicas de campo para marcaje topográfico
- A partir de aquí el proceso se **bifurca** según el tipo de derecho:

**Fase 3A: Matriz de Derechos Colectivos (Uso Común)**
- **COP Original**: Asamblea anuencia → Firma → Inscripción RAN (acta y convenio)
- **Modificatorio**: Ajustes al COP original (montos, superficie)
- **Superficie Adicional**: Nueva asamblea + nuevo ciclo RAN para superficie descubierta posteriormente
- **Obras Complementarias**: **Nuevo ciclo completo** (asamblea + RAN) documentado con campos "_2"

**Fase 3B: Matriz de Derechos Individuales (Parcelas)**
- **COP Original**: Negociación privada → Firma → Inscripción RAN
- **Modificatorio Individual**: Solo ajuste de montos (sin superficie ni BDT)
- **Ampliación**: Nueva superficie afectada de la misma parcela
- **Ampliación Remanente**: Superficie remanente de ampliación

**Fase 4: Matriz FIFONAFE e Informes de No Conflictos**
- Cadena de oficios interinstitucionales (FIFONAFE ↔ DGAOPR ↔ PA)
- Dispersión de fondos:
  - **Individuales**: Pago directo al titular
  - **Colectivos**: Depósito en FIFONAFE → Asamblea de retiro de fondos → Distribución

**Puntos Críticos del Flujo**:
1. Las tierras de uso común (colectivas) son **inalienables** - requieren asamblea obligatoriamente
2. Las parcelas individuales tienen titular específico - negociación directa sin asamblea
3. Obras Complementarias es un convenio variante que requiere **nuevo ciclo completo** (no es modificación)
4. Los campos RAN "_2" capturan este segundo ciclo en la **misma fila** del expediente

### Arquitectura de Alto Nivel

El sistema sigue una arquitectura de tres capas con extensiones geoespaciales:

```
┌──────────────────────────────────────────────────────┐
│            Capa de Presentación                      │
│   (Aplicación Web Responsiva - React/Vue)            │
│   - Mapa Interactivo (Leaflet.js)                    │
│   - Herramientas de Dibujo Geográfico                │
│   - Paneles de Información Contextual                │
│   - Tableros de Control                              │
└──────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────┐
│            Capa de Aplicación                        │
│  (REST API - Node.js/Express o Python/FastAPI)       │
│  - Servicios de Negocio                              │
│  - Servicio GIS (Transformación de Coordenadas)      │
│  - Motor de Cálculos Geoespaciales                   │
│  - Servicio de Visualización de Mapas                │
│  - Control de Acceso                                 │
│  - Validación de Geometrías                          │
└──────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────┐
│             Capa de Datos                            │
│  (PostgreSQL con extensión PostGIS)                  │
│  - Modelo Relacional                                 │
│  - Tipos de Datos Geométricos (GEOMETRY)             │
│  - Índices Espaciales (GiST)                         │
│  - Funciones Espaciales (ST_*)                       │
│  - Auditoría                                         │
│  - Integridad Referencial                            │
└──────────────────────────────────────────────────────┘
```


## Arquitectura

### Patrón Arquitectónico

El sistema utiliza una **arquitectura de tres capas con servicios geoespaciales** con separación clara de responsabilidades:

1. **Capa de Presentación**: Interfaz de usuario web responsiva con componentes de mapa interactivo
2. **Capa de Aplicación**: Lógica de negocio, servicios REST API y motor GIS
3. **Capa de Datos**: Persistencia en base de datos relacional con extensión PostGIS para datos geoespaciales

### Decisiones Arquitectónicas Clave

**DA-1: Base de Datos Relacional con PostGIS**
- **Decisión**: Utilizar PostgreSQL con extensión PostGIS como SGBD principal
- **Justificación**: 
  - Soporte nativo para integridad referencial compleja
  - PostGIS proporciona tipos de datos geométricos (GEOMETRY) y funciones espaciales completas (ST_Intersects, ST_Area, ST_Transform, etc.)
  - Índices espaciales GiST para consultas geométricas eficientes
  - Soporte para múltiples sistemas de coordenadas (SRID)
  - Excelente soporte para transacciones ACID
  - Capacidades de auditoría mediante triggers
  - Amplia adopción en sistemas GIS empresariales
- **Alternativas Consideradas**: MySQL con extensión espacial (funcionalidad GIS limitada), MongoDB con índices geoespaciales (no adecuado para relaciones complejas y cálculos geométricos precisos)

**DA-2: API REST con Autenticación JWT**
- **Decisión**: Implementar API RESTful con tokens JWT para autenticación
- **Justificación**:
  - Stateless, escalable para múltiples usuarios concurrentes
  - JWT permite control de acceso basado en roles incluyendo permisos específicos para Geógrafos
  - Facilita integración futura con aplicaciones móviles
- **Alternativas Consideradas**: Sesiones basadas en servidor (menos escalable)

**DA-3: Control de Acceso Basado en Roles (RBAC) con Rol de Geógrafo**
- **Decisión**: Implementar cuatro roles: Administrador, Usuario_Captura, Usuario_Visualizador y Geógrafo
- **Justificación**:
  - Seguridad por principio de mínimo privilegio
  - Separación clara entre captura administrativa, captura geográfica y visualización
  - Rol de Geógrafo con permisos específicos para crear/editar geometrías
  - Auditoría de acciones por rol
- **Alternativas Consideradas**: Permisos granulares por recurso (demasiado complejo para caso de uso)

**DA-4: Auditoría Automática mediante Triggers de Base de Datos**
- **Decisión**: Implementar auditoría mediante triggers en PostgreSQL
- **Justificación**:
  - Garantiza que ninguna modificación escape de auditoría (incluyendo cambios geométricos)
  - Rendimiento superior a auditoría en capa de aplicación
  - Captura incluso cambios directos a BD
- **Alternativas Consideradas**: Auditoría en capa de aplicación (puede omitirse en accesos directos)

**DA-5: Librería de Mapas Web (Leaflet.js)**
- **Decisión**: Utilizar Leaflet.js como librería principal para visualización de mapas
- **Justificación**:
  - Código abierto y amplia adopción en aplicaciones GIS web
  - Ligera y eficiente para renderizado de geometrías
  - Soporte para plugins de dibujo (Leaflet.draw) y edición de geometrías
  - Compatible con múltiples capas base (OpenStreetMap, imágenes satelitales)
  - Soporte para GeoJSON como formato de intercambio
  - Personalizable mediante CSS y JavaScript
- **Alternativas Consideradas**: OpenLayers (más complejo pero más potente), Google Maps API (licenciamiento y costos), Mapbox GL JS (requiere cuenta y puede tener costos)

**DA-6: Cálculo de Intersecciones en Base de Datos**
- **Decisión**: Realizar cálculos de intersecciones geométricas mediante funciones PostGIS en la base de datos
- **Justificación**:
  - Aprovecha el motor geoespacial optimizado de PostGIS
  - Minimiza transferencia de datos entre aplicación y BD
  - Índices espaciales GiST aceleran consultas de intersección
  - Precisión y consistencia en cálculos geométricos
  - Menor latencia para cálculos complejos
- **Alternativas Consideradas**: Cálculos en capa de aplicación con bibliotecas como Turf.js (menos eficiente, mayor transferencia de datos)

**DA-7: Transformación de Coordenadas Dual (WGS84/UTM)**
- **Decisión**: Almacenar geometrías en WGS84 (EPSG:4326) y transformar a UTM bajo demanda
- **Justificación**:
  - WGS84 es estándar para mapas web y Leaflet.js
  - Transformación a UTM cuando se requiera para documentos jurídicos mediante ST_Transform de PostGIS
  - Evita duplicación de datos geométricos
  - Facilita interoperabilidad con servicios de mapas estándar
- **Alternativas Consideradas**: Almacenar en UTM (complica visualización web), almacenar ambos sistemas (duplicación y riesgo de inconsistencia)

**DA-8: Importación Excel y Archivos Geoespaciales**
- **Decisión**: Utilizar bibliotecas especializadas para Excel (xlsx, openpyxl) y geoespaciales (GDAL/OGR, fiona, shapely)
- **Justificación**:
  - Mantiene compatibilidad con flujo de trabajo actual (Excel)
  - GDAL/OGR soporta múltiples formatos geoespaciales (Shapefile, KML, GeoJSON)
  - Validación antes de inserción protege integridad
  - Generación de reportes de errores facilita corrección
  - Lectura automática de sistemas de coordenadas desde archivos .prj
- **Alternativas Consideradas**: Conversión manual (propenso a errores), APIs de servicios en la nube (dependencia externa)


## Components and Interfaces

El diseño de las interfaces de TypeScript ha sido alineado con la estructura relacional definida en la base de datos.
**Nota Arquitectónica**: Todas las llaves primarias (`id_*`) y foráneas se definen como `number` para reflejar el uso nativo de `SERIAL` (enteros autoincrementables) en PostgreSQL, garantizando máximo rendimiento en cruces geográficos e indexación.

### Módulo de Autenticación y Autorización

```typescript
interface AuthService {
  login(correo: string, contrasena: string): Promise<AuthToken>
  validateToken(token: string): Promise<Usuario>
  logout(token: string): Promise<void>
  checkPermission(id_usuario: number, resource: string, operation: 'read' | 'write'): Promise<boolean>
}

interface AuthToken {
  token: string
  expiresAt: Date
  id_usuario: number // FK a Usuario
  rol: 'admin' | 'operador' | 'analista' | 'geografo'
}

interface Usuario {
  id_usuario: number // PK SERIAL
  nombre: string
  apellido_paterno: string
  apellido_materno: string | null
  correo: string
  rol: 'admin' | 'operador' | 'analista' | 'geografo'
  activo: boolean
  fecha_alta: Date
  fecha_baja: Date | null
  observaciones: string | null
}
```

### Módulo de Catálogos Geográficos

```typescript
interface CatalogoService {
  listEntidades(): Promise<EntidadFederativa[]>
  listMunicipios(id_entidad: number): Promise<Municipio[]>
}

interface EntidadFederativa {
  id_entidad: number // PK SERIAL
  clave_inegi: string
  nombre: string
  activo: boolean
}

interface Municipio {
  id_municipio: number // PK SERIAL
  id_entidad: number // FK a EntidadFederativa
  clave_inegi: string
  nombre: string
  activo: boolean
}
```

### Módulo de Gestión Territorial (Tramos y Frentes)

```typescript
interface TerritorialService {
  getTramoById(id_tramo: number): Promise<Tramo>
  listTramos(): Promise<Tramo[]>
  listFrentesByTramo(id_tramo: number): Promise<Frente[]>
  getTramoNucleoIntersect(id_tramo: number, id_frente: number, id_nucleo: number): Promise<TramoNucleo>
}

interface Tramo {
  id_tramo: number // PK SERIAL
  clave_tramo: string
  nombre_tramo: string
  descripcion: string | null
  geometria_linea: GeoJSON | null
  activo: boolean
  fecha_registro: Date
  observaciones: string | null
}

interface Frente {
  id_frente: number // PK SERIAL
  id_tramo: number // FK a Tramo
  clave_frente: string
  nombre_frente: string
  descripcion: string | null
  geometria_linea: GeoJSON | null
  activo: boolean
  fecha_registro: Date
  observaciones: string | null
}

interface TramoNucleo {
  id_tramo_nucleo: number // PK SERIAL
  id_tramo: number // FK a Tramo
  id_frente: number // FK a Frente
  id_nucleo: number // FK a NucleoAgrario
  consecutivo: number
  numero_tramo: string | null
  geometria_segmento: GeoJSON | null
  longitud_m: number | null
  es_expropiacion: boolean
  causa_problema: string | null
  proyecto_no_afecta_uso_comun: boolean | null
  observaciones: string | null
}
```

### Módulo de Núcleos Agrarios y Parcelas

```typescript
interface NucleoAgrarioService {
  getNucleoById(id_nucleo: number): Promise<NucleoAgrario>
  listNucleos(): Promise<NucleoAgrario[]>
  getORVByNucleo(id_nucleo: number): Promise<ORV | null>
  listParcelasByNucleo(id_nucleo: number): Promise<Parcela[]>
}

interface NucleoAgrario {
  id_nucleo: number // PK SERIAL
  id_municipio: number // FK a Municipio
  nombre_nucleo: string
  tipo_nucleo: 'ejido' | 'comunidad'
  comunidad_indigena: boolean
  residencia: string | null
  geometria_poligono: GeoJSON | null
  fecha_creacion: Date
  observaciones: string | null
}

interface PadronHistorial {
  id_padron: number // PK SERIAL
  id_nucleo: number // FK a NucleoAgrario
  fecha_padron: Date
  numero_ejidatarios_comuneros: number
  id_usuario_registro: number | null // FK a Usuario
  fecha_registro: Date
  observaciones: string | null
}

interface ORV {
  id_orv: number // PK SERIAL
  id_nucleo: number // FK a NucleoAgrario
  numero_orv: string | null
  inicio_vigencia: Date
  fin_vigencia: Date
  orv_vigente: boolean
  acta_eleccion_inscrita_ran: boolean
  documentacion_disponible: boolean
  documentacion_faltante: string | null
  comisariado_presidente: string | null
  comisariado_secretario: string | null
  comisariado_tesorero: string | null
  consejo_vigilancia_presidente: string | null
  consejo_vigilancia_secretario1: string | null
  consejo_vigilancia_secretario2: string | null
  observaciones: string | null
}

interface Parcela {
  id_parcela: number // PK SERIAL
  id_nucleo: number // FK a NucleoAgrario
  tipo_parcela: 'individual' | 'copropiedad' | null
  no_parcela_ppt: string | null
  certificado_parcelario: string | null
  folio_derechos: string | null
  constancia_vigencia_fecha: Date | null
  nombre_titular: string | null
  documentacion_disponible: boolean
  documentacion_faltante: string | null
  observaciones: string | null
}
```

### Módulo de Afectaciones y Procesos (Operativo)

```typescript
interface ProcesoOperativoService {
  listAfectaciones(id_tramo_nucleo: number): Promise<Afectacion[]>
  listActividadesCampo(id_tramo_nucleo: number): Promise<ActividadCampo[]>
  listAsambleas(id_tramo_nucleo: number): Promise<Asamblea[]>
  listConvenios(id_tramo_nucleo: number): Promise<Convenio[]>
  getTramiteFifonafe(id_tramo_nucleo: number): Promise<TramiteFifonafe[]>
}

interface Afectacion {
  id_afectacion: number // PK SERIAL
  id_nucleo: number // FK a NucleoAgrario
  id_tramo_nucleo: number // FK a TramoNucleo
  id_parcela: number | null // FK a Parcela (Solo para individuales)
  tipo_afectacion: 'colectivo' | 'individual'
  tipo_tenencia: string
  subtipo_tenencia: string | null
  destino_superficie: string | null
  no_parcela_solar: string | null
  superficie_afectada_ha: number | null
  num_personas_afectadas: number | null
  situacion_juridica: string | null
  documentacion_disponible: boolean
  documentacion_faltante: string | null
  observaciones: string | null
}

interface ActividadCampo {
  id_actividad: number // PK SERIAL
  id_tramo_nucleo: number // FK a TramoNucleo
  tipo_actividad: 'sensibilizacion' | 'caminamiento'
  contexto_proceso: string
  fecha_programada: Date | null
  fecha_realizada: Date | null
  resultado: string | null
  id_usuario_registro: number | null // FK a Usuario
  fecha_registro: Date
  observaciones: string | null
}

interface Asamblea {
  id_asamblea: number // PK SERIAL
  id_tramo_nucleo: number // FK a TramoNucleo
  tipo_asamblea: 'informacion' | 'anuencia' | 'retiro_fondos' | 'conciliacion' | 'no_verificativo'
  estatus_asamblea: 'programado' | 'pendiente' | 'completo' | null
  contexto_proceso: string | null
  fecha_exp_1a: Date | null
  fecha_prog_1a: Date | null
  fecha_exp_2a: Date | null
  fecha_prog_2a: Date | null
  fecha_realizada: Date | null
  resultado_anuencia: 'otorgada' | 'negada' | 'pendiente' | 'no_aplica'
  ingreso_ran_fecha: Date | null
  numero_solicitud_ran: string | null
  calificacion_registral_ran: string | null
  acta_inscripcion_fecha_ran: Date | null
  documentacion_disponible: boolean
  documentacion_faltante: string | null
  id_padron: number | null // FK a PadronHistorial (Quórum legal)
  id_usuario_registro: number | null // FK a Usuario
  observaciones: string | null
}

interface Convenio {
  id_convenio: number // PK SERIAL
  id_tramo_nucleo: number // FK a TramoNucleo
  id_afectacion: number // FK a Afectacion
  id_convenio_padre: number | null // FK recursiva a Convenio
  id_asamblea_autorizacion: number | null // FK a Asamblea
  tipo_afectacion: 'colectivo' | 'individual'
  tipo_convenio: 'cop_original' | 'modificatorio' | 'superficie_adicional' | 'obras_complementarias' | 'ampliacion' | 'ampliacion_remanente'
  fecha_firma: Date | null
  monto_100: number | null
  monto_90: number | null
  monto_bdt: number | null
  
  /**
   * superficie_total_ha: Usado EXCLUSIVAMENTE para afectaciones INDIVIDUALES (derechos individuales)
   * Representa la superficie específica de la PARCELA afectada que tiene un dueño particular.
   * Se captura en expedientes privados mediante negociación directa con el titular.
   * La distinción es jurídica: estas parcelas tienen titular específico y no requieren asamblea.
   * 
   * IMPORTANTE: No usar para afectaciones colectivas. Ver superficie_real_afectada_ha.
   */
  superficie_total_ha: number | null
  
  /**
   * superficie_real_afectada_ha: Usado EXCLUSIVAMENTE para afectaciones COLECTIVAS (derechos colectivos)
   * Representa la superficie de TIERRAS DE USO COMÚN que pertenecen al núcleo agrario completo.
   * Estas tierras son INALIENABLES y su afectación requiere proceso de asamblea.
   * La distinción es jurídica: no son propiedad de individuos sino del núcleo agrario.
   * 
   * IMPORTANTE: No usar para afectaciones individuales. Ver superficie_total_ha.
   */
  superficie_real_afectada_ha: number | null
  
  superficie_adicional_ha: number | null
  superficie_ampliacion_ha: number | null
  
  // Campos RAN estándar
  ingreso_ran_fecha: Date | null
  numero_solicitud_ingreso: string | null
  calificacion_registral: string | null
  convenio_inscrito_fecha_ran: Date | null
  
  documentacion_disponible: boolean
  documentacion_faltante: string | null
  id_usuario_registro: number | null // FK a Usuario
  observaciones: string | null
}

interface TramiteFifonafe {
  id_tramite_fifonafe: number // PK SERIAL
  id_tramo_nucleo: number // FK a TramoNucleo
  id_convenio: number | null // FK a Convenio
  id_afectacion: number | null // FK a Afectacion
  tipo_afectacion: 'colectivo' | 'individual'
  tipo_tramite: 'indemnizacion' | 'informe_no_conflictos'
  estatus: 'programado' | 'pendiente' | 'completo' | 'cancelado'
  hay_conflictos: boolean | null
  no_oficio_fifonafe_a_dgaopr: string | null
  no_oficio_dgaopr_a_repr: string | null
  no_oficio_rpta_repr_a_dgaopr: string | null
  no_oficio_rpta_dgaopr_a_fifonafe: string | null
  fecha_oficio_fifonafe_a_dgaopr: Date | null
  fecha_oficio_dgaopr_a_repr: Date | null
  fecha_oficio_rpta_repr_a_dgaopr: Date | null
  fecha_oficio_rpta_dgaopr_a_fifonafe: Date | null
  observaciones: string | null
}
```

### Módulo de Gestión Documental y Alertas

```typescript
interface DocumentacionSoporte {
  id_documento: number // PK SERIAL
  entidad_relacionada_id: number // ID dinámico (puede apuntar a nucleo, afectacion, convenio u orv)
  entidad_relacionada_tipo: 'nucleo_agrario' | 'afectacion' | 'convenio' | 'orv'
  tipo_documento: string
  categoria: 'disponible' | 'faltante'
  es_critico: boolean
  url_archivo: string | null
  observaciones: string | null
  fecha_carga: Date
}

interface Alerta {
  id_alerta: number // PK SERIAL
  tipo: 'vencimiento_orv' | 'evento_proximo' | 'documento_faltante'
  prioridad: 'alta' | 'media' | 'baja'
  titulo: string
  descripcion: string
  entidad_relacionada_id: number // ID dinámico de la entidad
  entidad_relacionada_tipo: string
  fecha_evento: Date | null
  esta_activa: boolean
  fecha_creacion: Date
}
```

## Data Models

### Modelo de Dominio

El siguiente diagrama muestra las entidades principales y sus relaciones, integrando el soporte nativo de la base de datos con módulos extendidos para la lógica de software:

```mermaid
erDiagram
    entidad_federativa ||--o{ municipio : "tiene"
    municipio ||--o{ nucleo_agrario : "contiene"
    
    usuario ||--o{ bitacora : "registra_auditoria"
    usuario ||--o{ usuario_frente : "asignado_a"
    frente ||--o{ usuario_frente : "asignado_a"
    
    tramo ||--|{ frente : "contiene"
    
    %% Optimización de cruce espacial
    tramo ||--o{ tramo_nucleo : "cruza"
    frente ||--o{ tramo_nucleo : "cruza"
    nucleo_agrario ||--o{ tramo_nucleo : "cruzado_por"
    
    nucleo_agrario ||--o| orv : "tiene_vigencia_y_padron"
    nucleo_agrario ||--o{ parcela : "tiene"
    
    tramo_nucleo ||--o{ afectacion : "genera"
    parcela ||--o{ afectacion : "afectada_por"
    
    tramo_nucleo ||--o{ actividad_campo : "sensibilizacion_y_caminamiento"
    tramo_nucleo ||--o{ asamblea : "aprueba"
    
    tramo_nucleo ||--o{ convenio : "tiene"
    afectacion ||--o{ convenio : "cubierta_por"
    asamblea ||--o| convenio : "autoriza"
    convenio ||--o| convenio : "modifica_a"
    
    tramo_nucleo ||--o{ tramite_fifonafe : "inicia"
    convenio ||--o| tramite_fifonafe : "respalda"
    afectacion ||--o| tramite_fifonafe : "respalda"
    
    %% Entidades de valor agregado (Integradas al SQL con SERIAL)
    nucleo_agrario ||--o{ documentacion_soporte : "almacena_evidencias"
    afectacion ||--o{ documentacion_soporte : "almacena_evidencias"
    
    nucleo_agrario ||--o{ alertas : "genera"
    usuario }o--o{ alertas_vistas : "lee"
    alertas ||--o{ alertas_vistas : "leída_por"
```

### Entidades de Base de Datos

Las entidades de la base de datos se corresponden con el esquema validado final, utilizando `SERIAL` para eficiencia, llaves foráneas explícitas y catálogos geográficos. Se incluyen adicionalmente las tablas de Documentación y Alertas alineadas a esta misma nomenclatura.

**1. Catálogos Geográficos**
```sql
CREATE TABLE entidad_federativa (
    id_entidad SERIAL PRIMARY KEY,
    clave_inegi CHAR(2) UNIQUE NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE municipio (
    id_municipio SERIAL PRIMARY KEY,
    id_entidad INTEGER NOT NULL REFERENCES entidad_federativa(id_entidad),
    clave_inegi CHAR(5) UNIQUE NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_municipio_entidad_clave UNIQUE (id_entidad, clave_inegi)
);
```

**2. Estructura Geográfica Principal**
```sql
CREATE TABLE tramo (
    id_tramo SERIAL PRIMARY KEY,
    clave_tramo VARCHAR(20) UNIQUE NOT NULL,
    nombre_tramo VARCHAR(200) NOT NULL,
    descripcion TEXT,
    geometria_linea GEOMETRY(MULTILINESTRING, 4326),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_registro DATE NOT NULL DEFAULT CURRENT_DATE,
    observaciones TEXT
);

CREATE TABLE frente (
    id_frente SERIAL PRIMARY KEY,
    id_tramo INTEGER NOT NULL REFERENCES tramo(id_tramo),
    clave_frente VARCHAR(30) NOT NULL,
    nombre_frente VARCHAR(200) NOT NULL,
    descripcion TEXT,
    geometria_linea GEOMETRY(MULTILINESTRING, 4326),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_registro DATE NOT NULL DEFAULT CURRENT_DATE,
    observaciones TEXT,
    CONSTRAINT uq_frente_tramo_clave UNIQUE (id_tramo, clave_frente),
    CONSTRAINT uq_frente_tramo_id UNIQUE (id_tramo, id_frente)
);

CREATE TABLE nucleo_agrario (
    id_nucleo SERIAL PRIMARY KEY,
    id_municipio INTEGER NOT NULL REFERENCES municipio(id_municipio),
    nombre_nucleo VARCHAR(300) NOT NULL,
    tipo_nucleo VARCHAR(20) NOT NULL CHECK (tipo_nucleo IN ('ejido', 'comunidad')),
    comunidad_indigena BOOLEAN NOT NULL DEFAULT FALSE,
    residencia VARCHAR(300),
    geometria_poligono GEOMETRY(MULTIPOLYGON, 4326),
    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    observaciones TEXT
);

CREATE TABLE tramo_nucleo (
    id_tramo_nucleo SERIAL PRIMARY KEY,
    id_tramo INTEGER NOT NULL REFERENCES tramo(id_tramo),
    id_frente INTEGER NOT NULL REFERENCES frente(id_frente),
    id_nucleo INTEGER NOT NULL REFERENCES nucleo_agrario(id_nucleo),
    consecutivo INTEGER NOT NULL,
    numero_tramo VARCHAR(50),
    geometria_segmento GEOMETRY(MULTILINESTRING, 4326),
    longitud_m NUMERIC(14,2) CHECK (longitud_m >= 0),
    es_expropiacion BOOLEAN NOT NULL DEFAULT FALSE,
    causa_problema TEXT,
    proyecto_no_afecta_uso_comun BOOLEAN,
    observaciones TEXT,
    CONSTRAINT uq_tramo_nucleo_consecutivo UNIQUE (id_tramo, consecutivo),
    CONSTRAINT fk_tramo_nucleo_frente_mismo_tramo
        FOREIGN KEY (id_tramo, id_frente) REFERENCES frente(id_tramo, id_frente),
    CONSTRAINT uq_tramo_nucleo_nucleo_id UNIQUE (id_nucleo, id_tramo_nucleo)
);
```

**3. Usuarios y Auditoría**
```sql
CREATE TABLE usuario (
    id_usuario SERIAL PRIMARY KEY,
    nombre VARCHAR(250) NOT NULL,
    apellido_paterno VARCHAR(250) NOT NULL,
    apellido_materno VARCHAR(250),
    correo VARCHAR(320) UNIQUE NOT NULL,
    contrasena_hash VARCHAR(255) NOT NULL,
    rol VARCHAR(30) NOT NULL CHECK (rol IN ('admin', 'operador', 'analista', 'geografo')),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_alta TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_baja TIMESTAMPTZ,
    observaciones TEXT
);

CREATE TABLE bitacora (
    id_bitacora BIGSERIAL PRIMARY KEY,
    id_usuario INTEGER NOT NULL REFERENCES usuario(id_usuario),
    id_nucleo INTEGER REFERENCES nucleo_agrario(id_nucleo),
    id_tramo_nucleo INTEGER REFERENCES tramo_nucleo(id_tramo_nucleo),
    entidad_tipo VARCHAR(100) NOT NULL,
    entidad_id BIGINT,
    accion VARCHAR(30) NOT NULL CHECK (accion IN ('insert', 'update', 'delete', 'validacion', 'cambio_estado', 'carga_documento')),
    detalle_cambio TEXT,
    valor_anterior JSONB,
    valor_nuevo JSONB,
    fecha_hora TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_origen INET,
    user_agent TEXT
);

CREATE TABLE usuario_frente (
    id_usuario INTEGER NOT NULL REFERENCES usuario(id_usuario),
    id_frente INTEGER NOT NULL REFERENCES frente(id_frente),
    fecha_asignacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (id_usuario, id_frente)
);
```

**4. Parcelas, ORV y Afectaciones**
```sql
CREATE TABLE orv (
    id_orv SERIAL PRIMARY KEY,
    id_nucleo INTEGER NOT NULL REFERENCES nucleo_agrario(id_nucleo),
    numero_orv VARCHAR(50),
    inicio_vigencia DATE NOT NULL,
    fin_vigencia DATE NOT NULL,
    orv_vigente BOOLEAN NOT NULL DEFAULT FALSE,
    acta_eleccion_inscrita_ran BOOLEAN NOT NULL DEFAULT FALSE,
    documentacion_disponible BOOLEAN NOT NULL DEFAULT FALSE,
    documentacion_faltante TEXT,
    comisariado_presidente VARCHAR(300),
    comisariado_secretario VARCHAR(300),
    comisariado_tesorero VARCHAR(300),
    consejo_vigilancia_presidente VARCHAR(300),
    consejo_vigilancia_secretario1 VARCHAR(300),
    consejo_vigilancia_secretario2 VARCHAR(300),
    observaciones TEXT
);

CREATE TABLE padron_historial (
    id_padron SERIAL PRIMARY KEY,
    id_nucleo INTEGER NOT NULL REFERENCES nucleo_agrario(id_nucleo),
    fecha_padron DATE NOT NULL,
    numero_ejidatarios_comuneros INTEGER NOT NULL CHECK (numero_ejidatarios_comuneros >= 0),
    id_usuario_registro INTEGER REFERENCES usuario(id_usuario),
    fecha_registro TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    observaciones TEXT
);

CREATE TABLE parcela (
    id_parcela SERIAL PRIMARY KEY,
    id_nucleo INTEGER NOT NULL REFERENCES nucleo_agrario(id_nucleo),
    tipo_parcela VARCHAR(30) CHECK (tipo_parcela IN ('individual', 'copropiedad')),
    no_parcela_ppt VARCHAR(50),
    certificado_parcelario VARCHAR(100),
    folio_derechos VARCHAR(100),
    constancia_vigencia_fecha DATE,
    nombre_titular VARCHAR(300),
    documentacion_disponible BOOLEAN NOT NULL DEFAULT FALSE,
    documentacion_faltante TEXT,
    observaciones TEXT,
    CONSTRAINT uq_parcela_nucleo_id UNIQUE (id_nucleo, id_parcela)
);

CREATE TABLE afectacion (
    id_afectacion SERIAL PRIMARY KEY,
    id_nucleo INTEGER NOT NULL REFERENCES nucleo_agrario(id_nucleo),
    id_tramo_nucleo INTEGER NOT NULL,
    id_parcela INTEGER,
    tipo_afectacion VARCHAR(20) NOT NULL CHECK (tipo_afectacion IN ('colectivo', 'individual')),
    tipo_tenencia VARCHAR(80) NOT NULL,
    subtipo_tenencia VARCHAR(80),
    destino_superficie VARCHAR(80),
    no_parcela_solar VARCHAR(100),
    superficie_afectada_ha NUMERIC(12,4) CHECK (superficie_afectada_ha >= 0),
    num_personas_afectadas INTEGER CHECK (num_personas_afectadas >= 0),
    situacion_juridica TEXT,
    documentacion_disponible BOOLEAN NOT NULL DEFAULT FALSE,
    documentacion_faltante TEXT,
    observaciones TEXT,
    CONSTRAINT fk_afectacion_tramo_nucleo_mismo_nucleo
        FOREIGN KEY (id_nucleo, id_tramo_nucleo) REFERENCES tramo_nucleo(id_nucleo, id_tramo_nucleo),
    CONSTRAINT fk_afectacion_parcela_mismo_nucleo
        FOREIGN KEY (id_nucleo, id_parcela) REFERENCES parcela(id_nucleo, id_parcela),
    CONSTRAINT uq_afectacion_tramo_id_tipo UNIQUE (id_tramo_nucleo, id_afectacion, tipo_afectacion)
);
```

**5. Proceso Operativo y Documentos**
```sql
CREATE TABLE actividad_campo (
    id_actividad SERIAL PRIMARY KEY,
    id_tramo_nucleo INTEGER NOT NULL REFERENCES tramo_nucleo(id_tramo_nucleo),
    tipo_actividad VARCHAR(50) NOT NULL CHECK (tipo_actividad IN ('sensibilizacion', 'caminamiento')),
    contexto_proceso VARCHAR(50) NOT NULL DEFAULT 'cop_original',
    fecha_programada DATE,
    fecha_realizada DATE,
    resultado TEXT,
    id_usuario_registro INTEGER REFERENCES usuario(id_usuario),
    fecha_registro TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    observaciones TEXT
);

CREATE TABLE asamblea (
    id_asamblea SERIAL PRIMARY KEY,
    id_tramo_nucleo INTEGER NOT NULL REFERENCES tramo_nucleo(id_tramo_nucleo),
    tipo_asamblea VARCHAR(50) NOT NULL CHECK (tipo_asamblea IN ('informacion', 'anuencia', 'retiro_fondos', 'conciliacion', 'no_verificativo')),
    contexto_proceso VARCHAR(50),
    fecha_exp_1a DATE,
    fecha_prog_1a DATE,
    fecha_exp_2a DATE,
    fecha_prog_2a DATE,
    fecha_realizada DATE,
    resultado_anuencia VARCHAR(30) NOT NULL DEFAULT 'pendiente' CHECK (resultado_anuencia IN ('otorgada', 'negada', 'pendiente', 'no_aplica')),
    estatus_asamblea VARCHAR(30) CHECK (estatus_asamblea IN ('programado', 'pendiente', 'completo')),
    ingreso_ran_fecha DATE,
    numero_solicitud_ran VARCHAR(100),
    calificacion_registral_ran TEXT,
    acta_inscripcion_fecha_ran DATE,
    documentacion_disponible BOOLEAN NOT NULL DEFAULT FALSE,
    documentacion_faltante TEXT,
    id_padron INTEGER REFERENCES padron_historial(id_padron),
    id_usuario_registro INTEGER REFERENCES usuario(id_usuario),
    observaciones TEXT,
    CONSTRAINT uq_asamblea_tramo_id UNIQUE (id_tramo_nucleo, id_asamblea)
);

CREATE TABLE convenio (
    id_convenio SERIAL PRIMARY KEY,
    id_tramo_nucleo INTEGER NOT NULL REFERENCES tramo_nucleo(id_tramo_nucleo),
    id_afectacion INTEGER NOT NULL,
    id_convenio_padre INTEGER,
    id_asamblea_autorizacion INTEGER,
    tipo_afectacion VARCHAR(20) NOT NULL CHECK (tipo_afectacion IN ('colectivo', 'individual')),
    tipo_convenio VARCHAR(50) NOT NULL CHECK (tipo_convenio IN (
        'cop_original', 'modificatorio', 'superficie_adicional', 'obras_complementarias',
        'ampliacion', 'ampliacion_remanente'
    )),
    fecha_firma DATE,
    monto_100 NUMERIC(18,2) CHECK (monto_100 >= 0),
    monto_90 NUMERIC(18,2) CHECK (monto_90 >= 0),
    monto_bdt NUMERIC(18,2) CHECK (monto_bdt >= 0),
    
    -- CAMPOS DE SUPERFICIE: Distinción jurídica por tipo de derecho afectado
    -- superficie_total_ha: Usado EXCLUSIVAMENTE para afectaciones INDIVIDUALES (derechos individuales)
    --   Representa la superficie específica de la PARCELA afectada que tiene un dueño particular.
    --   Se captura en expedientes privados mediante negociación directa con el titular.
    --   La distinción es jurídica: estas parcelas tienen titular específico y no requieren asamblea.
    --   IMPORTANTE: No usar para afectaciones colectivas. Ver superficie_real_afectada_ha.
    superficie_total_ha NUMERIC(12,4) CHECK (superficie_total_ha >= 0),
    
    -- superficie_real_afectada_ha: Usado EXCLUSIVAMENTE para afectaciones COLECTIVAS (derechos colectivos)
    --   Representa la superficie de TIERRAS DE USO COMÚN que pertenecen al núcleo agrario completo.
    --   Estas tierras son INALIENABLES y su afectación requiere proceso de asamblea.
    --   La distinción es jurídica: no son propiedad de individuos sino del núcleo agrario.
    --   IMPORTANTE: No usar para afectaciones individuales. Ver superficie_total_ha.
    superficie_real_afectada_ha NUMERIC(12,4) CHECK (superficie_real_afectada_ha >= 0),
    
    superficie_adicional_ha NUMERIC(12,4) CHECK (superficie_adicional_ha >= 0),
    superficie_ampliacion_ha NUMERIC(12,4) CHECK (superficie_ampliacion_ha >= 0),
    
    -- Campos RAN estándar
    ingreso_ran_fecha DATE,
    numero_solicitud_ingreso VARCHAR(100),
    calificacion_registral TEXT,
    convenio_inscrito_fecha_ran DATE,
    
    documentacion_disponible BOOLEAN NOT NULL DEFAULT FALSE,
    documentacion_faltante TEXT,
    id_usuario_registro INTEGER REFERENCES usuario(id_usuario),
    observaciones TEXT,
    CONSTRAINT fk_convenio_afectacion_compuesta
        FOREIGN KEY (id_tramo_nucleo, id_afectacion, tipo_afectacion)
        REFERENCES afectacion(id_tramo_nucleo, id_afectacion, tipo_afectacion),
    CONSTRAINT fk_convenio_padre_recursiva
        FOREIGN KEY (id_tramo_nucleo, id_convenio_padre, tipo_afectacion)
        REFERENCES convenio(id_tramo_nucleo, id_convenio, tipo_afectacion),
    CONSTRAINT fk_convenio_asamblea_compuesta
        FOREIGN KEY (id_tramo_nucleo, id_asamblea_autorizacion)
        REFERENCES asamblea(id_tramo_nucleo, id_asamblea),
    -- Validar que tipo_convenio sea coherente con tipo_afectacion
    CONSTRAINT chk_tipo_convenio_por_afectacion CHECK (
        (tipo_afectacion = 'colectivo' AND tipo_convenio IN ('cop_original', 'modificatorio', 'superficie_adicional', 'obras_complementarias'))
        OR
        (tipo_afectacion = 'individual' AND tipo_convenio IN ('cop_original', 'modificatorio', 'ampliacion', 'ampliacion_remanente'))
    ),
    -- Regla: Obras Complementarias NO captura monto BDT (según proceso)
    CONSTRAINT chk_bdt_no_obras_complementarias CHECK (
        (tipo_convenio = 'obras_complementarias' AND monto_bdt IS NULL)
        OR
        (tipo_convenio != 'obras_complementarias')
    ),
    -- Regla: Modificatorio Individual solo requiere fecha, monto_90, monto_100 (sin superficie, sin BDT, sin RAN)
    CONSTRAINT chk_modificatorio_individual_restricciones CHECK (
        NOT (tipo_convenio = 'modificatorio' AND tipo_afectacion = 'individual')
        OR
        (superficie_total_ha IS NULL 
         AND superficie_real_afectada_ha IS NULL 
         AND superficie_adicional_ha IS NULL
         AND superficie_ampliacion_ha IS NULL
         AND monto_bdt IS NULL
         AND ingreso_ran_fecha IS NULL
         AND numero_solicitud_ingreso IS NULL
         AND calificacion_registral IS NULL
         AND convenio_inscrito_fecha_ran IS NULL)
    ),
    -- Regla: Exclusividad estricta de campos de superficie según el tipo de convenio y afectación
    CONSTRAINT chk_superficie_exclusiva_estricta CHECK (
        (tipo_afectacion != 'individual' OR (superficie_real_afectada_ha IS NULL AND superficie_adicional_ha IS NULL))
        AND
        (tipo_afectacion != 'colectivo' OR (superficie_total_ha IS NULL AND superficie_ampliacion_ha IS NULL))
        AND
        (tipo_convenio != 'cop_original' OR tipo_afectacion != 'individual' OR superficie_ampliacion_ha IS NULL)
        AND
        (tipo_convenio NOT IN ('ampliacion', 'ampliacion_remanente') OR superficie_total_ha IS NULL)
        AND
        (tipo_convenio != 'superficie_adicional' OR superficie_real_afectada_ha IS NULL)
        AND
        (tipo_convenio NOT IN ('cop_original', 'obras_complementarias') OR tipo_afectacion != 'colectivo' OR superficie_adicional_ha IS NULL)
    )
);

CREATE TABLE tramite_fifonafe (
    id_tramite_fifonafe SERIAL PRIMARY KEY,
    id_tramo_nucleo INTEGER NOT NULL REFERENCES tramo_nucleo(id_tramo_nucleo),
    id_convenio INTEGER,
    id_afectacion INTEGER,
    tipo_afectacion VARCHAR(20) NOT NULL CHECK (tipo_afectacion IN ('colectivo', 'individual')),
    tipo_tramite VARCHAR(50) NOT NULL CHECK (tipo_tramite IN ('indemnizacion', 'informe_no_conflictos')),
    estatus VARCHAR(30) NOT NULL DEFAULT 'pendiente' CHECK (estatus IN ('programado', 'pendiente', 'completo', 'cancelado')),
    hay_conflictos BOOLEAN,
    no_oficio_fifonafe_a_dgaopr VARCHAR(50),
    no_oficio_dgaopr_a_repr VARCHAR(50),
    no_oficio_rpta_repr_a_dgaopr VARCHAR(50),
    no_oficio_rpta_dgaopr_a_fifonafe VARCHAR(50),
    fecha_oficio_fifonafe_a_dgaopr DATE,
    fecha_oficio_dgaopr_a_repr DATE,
    fecha_oficio_rpta_repr_a_dgaopr DATE,
    fecha_oficio_rpta_dgaopr_a_fifonafe DATE,
    observaciones TEXT,
    CONSTRAINT fk_tramite_convenio_compuesta
        FOREIGN KEY (id_tramo_nucleo, id_convenio, tipo_afectacion)
        REFERENCES convenio(id_tramo_nucleo, id_convenio, tipo_afectacion),
    CONSTRAINT fk_tramite_afectacion_compuesta
        FOREIGN KEY (id_tramo_nucleo, id_afectacion, tipo_afectacion)
        REFERENCES afectacion(id_tramo_nucleo, id_afectacion, tipo_afectacion)
);
```

**6. Módulo de Alertas y Documentación Soporte (Integrado)**
```sql
CREATE TABLE documentacion_soporte (
    id_documento SERIAL PRIMARY KEY,
    entidad_relacionada_id INTEGER NOT NULL,
    entidad_relacionada_tipo VARCHAR(50) NOT NULL CHECK (entidad_relacionada_tipo IN ('nucleo_agrario', 'afectacion', 'convenio', 'orv')),
    tipo_documento VARCHAR(100) NOT NULL,
    categoria VARCHAR(20) NOT NULL CHECK (categoria IN ('disponible', 'faltante')),
    es_critico BOOLEAN NOT NULL DEFAULT FALSE,
    url_archivo TEXT,
    observaciones TEXT,
    fecha_carga TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE alertas (
    id_alerta SERIAL PRIMARY KEY,
    tipo VARCHAR(50) NOT NULL CHECK (tipo IN ('vencimiento_orv', 'evento_proximo', 'documento_faltante')),
    prioridad VARCHAR(10) NOT NULL CHECK (prioridad IN ('alta', 'media', 'baja')),
    titulo VARCHAR(255) NOT NULL,
    descripcion TEXT,
    entidad_relacionada_id INTEGER NOT NULL,
    entidad_relacionada_tipo VARCHAR(50) NOT NULL,
    fecha_evento DATE,
    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    esta_activa BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE alertas_vistas (
    id_alerta INTEGER NOT NULL REFERENCES alertas(id_alerta) ON DELETE CASCADE,
    id_usuario INTEGER NOT NULL REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    fecha_vista TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id_alerta, id_usuario)
);

-- Índices Espaciales y de Rendimiento
CREATE INDEX idx_tramo_geometria ON tramo USING GIST (geometria_linea);
CREATE INDEX idx_frente_geometria ON frente USING GIST (geometria_linea);
CREATE INDEX idx_nucleo_geometria ON nucleo_agrario USING GIST (geometria_poligono);
CREATE INDEX idx_tramo_nucleo_geometria ON tramo_nucleo USING GIST (geometria_segmento);

-- Triggers de Reglas de Negocio (Excepciones de Dominio)
CREATE OR REPLACE FUNCTION fn_validar_afectacion_uso_comun() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.tipo_afectacion = 'colectivo' THEN
        IF EXISTS (SELECT 1 FROM tramo_nucleo WHERE id_tramo_nucleo = NEW.id_tramo_nucleo AND proyecto_no_afecta_uso_comun = TRUE) THEN
            RAISE EXCEPTION 'No se pueden crear afectaciones colectivas si el proyecto no afecta uso común';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validar_afectacion_uso_comun
BEFORE INSERT OR UPDATE ON afectacion
FOR EACH ROW EXECUTE FUNCTION fn_validar_afectacion_uso_comun();

CREATE OR REPLACE FUNCTION fn_validar_convenio_expropiacion() RETURNS TRIGGER AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM tramo_nucleo WHERE id_tramo_nucleo = NEW.id_tramo_nucleo AND es_expropiacion = TRUE) THEN
        RAISE EXCEPTION 'No se pueden registrar convenios en un tramo-núcleo marcado como Expropiación Directa';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validar_convenio_expropiacion
BEFORE INSERT OR UPDATE ON convenio
FOR EACH ROW EXECUTE FUNCTION fn_validar_convenio_expropiacion();
```

### Vistas de Base de Datos

Las vistas integran el cálculo espacial y las relaciones del esquema final (usando `vw_dashboard_liberacion` y dependencias) para proveer datos a los tableros de control.

**Vista: vw_convenio_estado**
Calcula el estado del flujo de trabajo de cada convenio basado en fechas clave. Esta vista evita la necesidad de un campo explícito de estado manteniendo las fechas como fuente de verdad.

```sql
CREATE OR REPLACE VIEW vw_convenio_estado AS
SELECT 
    c.*,
    CASE 
        WHEN c.convenio_inscrito_fecha_ran IS NOT NULL THEN 'inscrito_ran'
        WHEN c.ingreso_ran_fecha IS NOT NULL THEN 'ingresado_ran'
        WHEN c.fecha_firma IS NOT NULL THEN 'firmado'
        ELSE 'borrador'
    END AS estado_calculado,
    -- Indicadores de validación
    (c.convenio_inscrito_fecha_ran IS NOT NULL) AS esta_inscrito_ran,
    (c.fecha_firma IS NOT NULL) AS esta_firmado
FROM convenio c;
```

**Vista: vw_tramo_nucleo_estado**
Evalúa en tiempo real si un cruce geográfico ya tiene convenios, trámites, o problemas documentados.
```sql
CREATE OR REPLACE VIEW vw_tramo_nucleo_estado AS
SELECT
    tn.id_tramo_nucleo,
    tn.id_tramo,
    tn.id_frente,
    tn.id_nucleo,
    tn.consecutivo,
    tn.longitud_m,
    tn.causa_problema,
    EXISTS (SELECT 1 FROM asamblea a WHERE a.id_tramo_nucleo = tn.id_tramo_nucleo AND a.resultado_anuencia = 'otorgada') AS tiene_anuencia,
    EXISTS (SELECT 1 FROM convenio c WHERE c.id_tramo_nucleo = tn.id_tramo_nucleo AND c.convenio_inscrito_fecha_ran IS NOT NULL) AS tiene_convenio_inscrito_ran,
    CASE
        WHEN (SELECT COUNT(*) FROM afectacion a WHERE a.id_tramo_nucleo = tn.id_tramo_nucleo) > 0 
             AND NOT EXISTS (
                 SELECT 1 FROM afectacion a 
                 WHERE a.id_tramo_nucleo = tn.id_tramo_nucleo 
                 AND NOT EXISTS (
                     SELECT 1 FROM convenio c 
                     WHERE c.id_afectacion = a.id_afectacion 
                     AND c.convenio_inscrito_fecha_ran IS NOT NULL
                 )
             ) THEN 'liberado'
        WHEN tn.es_expropiacion = TRUE THEN 'problema'
        WHEN NULLIF(BTRIM(tn.causa_problema), '') IS NOT NULL THEN 'problema'
        WHEN EXISTS (SELECT 1 FROM convenio c WHERE c.id_tramo_nucleo = tn.id_tramo_nucleo) THEN 'en_proceso'
        ELSE 'pendiente'
    END AS estado_operativo_calculado
FROM tramo_nucleo tn;
```

**Vista: vw_dashboard_liberacion**
Agrupa las afectaciones, convenios y estatus para análisis global.
```sql
CREATE OR REPLACE VIEW vw_dashboard_liberacion AS
SELECT
    v.id_tramo_nucleo,
    t.id_tramo,
    t.clave_tramo,
    f.id_frente,
    n.id_nucleo,
    n.nombre_nucleo,
    ef.nombre AS entidad_federativa,
    v.estado_operativo_calculado,
    COALESCE(af.total_superficie_afectada_ha, 0) AS total_superficie_afectada_ha,
    COALESCE(cv.total_convenios, 0) AS total_convenios,
    COALESCE(cv.total_monto_100, 0) AS total_monto_100
FROM vw_tramo_nucleo_estado v
JOIN tramo t ON t.id_tramo = v.id_tramo
JOIN frente f ON f.id_frente = v.id_frente
JOIN nucleo_agrario n ON n.id_nucleo = v.id_nucleo
JOIN municipio m ON m.id_municipio = n.id_municipio
JOIN entidad_federativa ef ON ef.id_entidad = m.id_entidad
LEFT JOIN (
    SELECT id_tramo_nucleo, SUM(COALESCE(superficie_afectada_ha, 0)) AS total_superficie_afectada_ha
    FROM afectacion GROUP BY id_tramo_nucleo
) af ON af.id_tramo_nucleo = v.id_tramo_nucleo
LEFT JOIN (
    SELECT id_tramo_nucleo, COUNT(*) AS total_convenios, SUM(COALESCE(monto_100, 0)) AS total_monto_100
    FROM convenio GROUP BY id_tramo_nucleo
) cv ON cv.id_tramo_nucleo = v.id_tramo_nucleo;
```

## Reglas de Negocio Implementadas en Base de Datos

Esta sección documenta las reglas de negocio críticas que se implementan mediante CHECK constraints en PostgreSQL para garantizar integridad de datos desde la capa de persistencia. Estas reglas provienen directamente del proceso descrito en `Descripción proceso.md` (fuente de verdad).

### RN-1: Validación de Tipo de Convenio por Tipo de Afectación

**Ubicación**: Tabla `convenio`, constraint `chk_tipo_convenio_por_afectacion`

**Regla**: Los tipos de convenio permitidos dependen del tipo de afectación:
- **Derechos Colectivos**: 'cop_original', 'modificatorio', 'superficie_adicional', 'obras_complementarias'
- **Derechos Individuales**: 'cop_original', 'modificatorio', 'ampliacion', 'ampliacion_remanente'

**Fuente**: `Descripción proceso.md`, líneas 35-39
> "Los tipos de convenio varían según el tipo de derecho afectado: para derechos colectivos incluye COP, Modificatorio, Superficie Adicional y Obras Complementarias; para derechos individuales incluye COP, Modificatorio, Ampliación y Ampliación Remanente."

**Implementación**:
```sql
CONSTRAINT chk_tipo_convenio_por_afectacion CHECK (
    (tipo_afectacion = 'colectivo' AND tipo_convenio IN ('cop_original', 'modificatorio', 'superficie_adicional', 'obras_complementarias'))
    OR
    (tipo_afectacion = 'individual' AND tipo_convenio IN ('cop_original', 'modificatorio', 'ampliacion', 'ampliacion_remanente'))
)
```

**Justificación**: Esta validación previene inconsistencias graves donde se crearía un convenio de "Ampliación" (que solo aplica a parcelas individuales) para una afectación colectiva, o viceversa con "Superficie Adicional" para una individual.

---

### RN-2: Obras Complementarias NO Captura Monto BDT

**Ubicación**: Tabla `convenio`, constraint `chk_bdt_no_obras_complementarias`

**Regla**: Los convenios de tipo 'obras_complementarias' NO deben tener valor en el campo `monto_bdt`. Este campo debe ser NULL para este tipo de convenio.

**Fuente**: `Descripción proceso.md`, línea 48
> "Se captura el Convenio Firmado (Fecha), montos (90%, 100%) y la Superficie Total Real Afectada (Ha). (Nota: En esta variante no se captura Monto BDT)."

**Implementación**:
```sql
CONSTRAINT chk_bdt_no_obras_complementarias CHECK (
    (tipo_convenio = 'obras_complementarias' AND monto_bdt IS NULL)
    OR
    (tipo_convenio != 'obras_complementarias')
)
```

**Justificación**: Las obras complementarias tienen una naturaleza distinta donde no se evalúan Bienes Distintos a la Tierra (BDT) en el avalúo. Esta restricción previene la captura errónea de montos BDT que no deberían existir en este tipo de convenio.

**Nota de Implementación**: Esta validación se realiza en base de datos para garantizar integridad incluso si múltiples aplicaciones o scripts acceden directamente a la BD.

---

### RN-3: Modificatorio Individual - Restricción de Campos

**Ubicación**: Tabla `convenio`, constraint `chk_modificatorio_individual_sin_superficie`

**Regla**: Los convenios de tipo 'modificatorio' con 'tipo_afectacion' = 'individual' NO deben capturar:
- `superficie_total_ha`
- `superficie_real_afectada_ha`
- `superficie_adicional_ha`
- `monto_bdt`

Solo se requieren: `fecha_firma`, `monto_90`, `monto_100`

**Fuente**: `Descripción proceso.md`, línea 59
> "Convenio Modificatorio: A diferencia de otros, el modificatorio individual solo requiere tres datos: Convenio Modificatorio (Fecha), Convenio Monto 90% y Convenio Monto 100%."

**Implementación**:
```sql
CONSTRAINT chk_modificatorio_individual_sin_superficie CHECK (
    NOT (tipo_convenio = 'modificatorio' 
         AND tipo_afectacion = 'individual' 
         AND (superficie_total_ha IS NOT NULL 
              OR superficie_real_afectada_ha IS NOT NULL 
              OR superficie_adicional_ha IS NOT NULL
              OR monto_bdt IS NOT NULL))
)
```

**Justificación**: El proceso de modificatorio individual es simplificado porque típicamente ajusta únicamente montos sin alterar superficie afectada. Esta restricción previene la captura de datos innecesarios que pueden confundir el análisis posterior.

**Nota Importante**: Esta regla NO aplica a modificatorios colectivos, que SÍ pueden tener superficie y monto BDT.

---

### RN-4: Campos RAN "2" Exclusivos para Obras Complementarias

**Ubicación**: Tabla `convenio`, campos `ingreso_ran_fecha_2`, `numero_solicitud_ingreso_2`, `calificacion_registral_2`, `acta_inscrita_fecha_ran_2`

**Regla**: Los campos RAN con sufijo "_2" SOLO deben poblarse cuando `tipo_convenio = 'obras_complementarias'`. Para todos los demás tipos de convenio, estos campos deben ser NULL.

**Fuente**: Confirmación del stakeholder (Procuraduría Agraria):
> "Al ser una nueva ocupación en tierras de uso común, la ley exige detonar de nuevo todo el ciclo [...] el sistema utiliza los campos Ingresado al RAN (Fecha) 2 y Número de Solicitud de Ingreso 2 como una nomenclatura diferenciada para evitar duplicidades en el sistema."

**Implementación**:
```sql
CONSTRAINT chk_campos_ran_2_solo_obras_complementarias CHECK (
    (tipo_convenio = 'obras_complementarias')
    OR
    (tipo_convenio != 'obras_complementarias' 
     AND ingreso_ran_fecha_2 IS NULL 
     AND numero_solicitud_ingreso_2 IS NULL 
     AND calificacion_registral_2 IS NULL 
     AND acta_inscrita_fecha_ran_2 IS NULL)
)
```

**Justificación**: Obras Complementarias requiere un nuevo ciclo completo de asamblea y trámite RAN por ser una nueva ocupación de tierras colectivas. Los campos "_2" son nomenclatura técnica para evitar colisiones con los campos del COP original, manteniendo ambos ciclos documentados en la misma fila del expediente. Esto refleja la práctica operativa donde un solo expediente contiene múltiples ciclos de autorización.

**Contexto Operativo Detallado**:
Las Obras Complementarias representan **una nueva ocupación de tierras de uso común** descubierta durante la ejecución del proyecto. Por ley, esto requiere detonar un **ciclo completamente nuevo** que incluye:
### RN-4: Normalización del Ciclo de Obras Complementarias

**Ubicación**: Tabla `asamblea` y tabla `convenio`

**Regla**: Los convenios de tipo 'obras_complementarias' requieren un nuevo ciclo completo de asamblea e inscripción RAN. Para preservar la normalización del modelo relacional, esto se implementa creando un nuevo registro en la tabla `asamblea` (con `contexto_proceso = 'obras_complementarias'`) y vinculándolo al nuevo convenio mediante la llave foránea `id_asamblea_autorizacion`. NO se deben duplicar campos registrales dentro de la tabla `convenio`.

**Fuente**: Confirmación del stakeholder (Procuraduría Agraria) e identificaciones de auditoría:
> "Al ser una nueva ocupación en tierras de uso común, la ley exige detonar de nuevo todo el ciclo [...]"

**Implementación**:
La tabla `asamblea` maneja su propio flujo registral RAN de manera independiente para cada evento comunitario, lo que permite asociar asambleas subsecuentes a convenios de obras complementarias sin corromper la integridad del expediente original.

**Justificación**: Obras Complementarias requiere un nuevo ciclo completo de asamblea y trámite RAN por ser una nueva ocupación de tierras colectivas. Evitar la des-normalización heredada del formato plano en Excel asegura una trazabilidad correcta del acta de asamblea independiente de los montos económicos del convenio.

**Contexto Operativo Detallado**:
Las Obras Complementarias representan **una nueva ocupación de tierras de uso común** descubierta durante la ejecución del proyecto. Por ley, esto requiere detonar un **ciclo completamente nuevo** que incluye:
1. Nueva asamblea de anuencia (porque es una nueva afectación al uso común)
2. Nueva inscripción de acta al RAN
3. Nuevo convenio con sus propios montos
4. Nueva inscripción del convenio al RAN

**Flujo de Obras Complementarias**:
1. **COP Original** (campos estándar):
   - Asamblea de anuencia → registro en tabla `asamblea`
   - Convenio firmado → `fecha_firma`
   - Ingreso al RAN → `ingreso_ran_fecha`, `numero_solicitud_ingreso`
   - Calificación → `calificacion_registral`
   - Inscripción → `convenio_inscrito_fecha_ran`

2. **Obras Complementarias** (nuevo ciclo relacional):
   - Nueva asamblea → nuevo registro en tabla `asamblea` con `contexto_proceso = 'obras_complementarias'`
   - Ingreso de nueva acta al RAN → administrado por la tabla `asamblea` (`ingreso_ran_fecha`, etc.)
   - Nuevo convenio firmado → nuevo registro en `convenio` vinculado a la nueva asamblea
   - Inscripción de nuevo convenio → campos RAN estándar del nuevo registro de `convenio`

---

### RN-5: Uso Diferenciado de Campos de Superficie según Tipo de Afectación

**Ubicación**: Tabla `convenio`, campos `superficie_total_ha` y `superficie_real_afectada_ha`

**Regla**: El campo de superficie a usar depende del tipo de afectación por razones jurídicas:
- **Afectaciones Individuales**: Usar `superficie_total_ha` (mide parcela con dueño específico)
- **Afectaciones Colectivas**: Usar `superficie_real_afectada_ha` (mide tierras de uso común inalienables)
- **Excepción**: Modificatorio Individual no usa ningún campo de superficie

**Fuente**: `Descripción proceso.md` y confirmación del stakeholder:
> "La distinción principal es jurídica. Superficie Total Real Afectada (Ha) mide el impacto sobre las tierras inalienables que son de uso comunal y requieren asambleas, mientras que Superficie Total (Ha.) se captura en expedientes privados para medir la afectación de una parcela particular con un dueño específico."

**Contexto Jurídico Detallado**:

Los dos campos de superficie reflejan una diferencia fundamental en el derecho agrario mexicano:

1. **`superficie_total_ha` - Para Derechos INDIVIDUALES (Parcelas)**:
   - Mide la superficie específica de una **parcela con titular registrado**
   - El titular es una persona física identificada (ejidatario o comunero)
   - Se captura en **expedientes privados** mediante negociación directa
   - **NO requiere asamblea** - la autorización la da el titular directamente
   - Proceso: Sensibilización → Caminamiento → Negociación privada → Firma
   - Ejemplo: "Parcela 45-Z, titular Juan Pérez, 2.5 hectáreas afectadas"

2. **`superficie_real_afectada_ha` - Para Derechos COLECTIVOS (Uso Común)**:
   - Mide la superficie de **tierras de uso común** del núcleo agrario
   - Estas tierras pertenecen al **núcleo agrario completo**, no a individuos
   - Son **inalienables** por ley (no se pueden vender ni transferir)
   - **REQUIERE asamblea** con quórum legal para su afectación
   - Proceso: Sensibilización → Caminamiento → Asamblea anuencia → Firma → RAN
   - Ejemplo: "Tierras de uso común del Ejido Los Pinos, 15.3 hectáreas afectadas"

**Importancia de la Distinción**:
- Confundir estos campos genera inconsistencias en el seguimiento legal
- Los reportes de liberación deben separar claramente derechos individuales vs colectivos
- Los montos de indemnización y procesos de pago son diferentes
- Los requisitos documentales ante el RAN son distintos

**Implementación**:
```sql
CONSTRAINT chk_superficie_exclusiva_estricta CHECK (
    (tipo_afectacion != 'individual' OR (superficie_real_afectada_ha IS NULL AND superficie_adicional_ha IS NULL))
    AND
    (tipo_afectacion != 'colectivo' OR (superficie_total_ha IS NULL AND superficie_ampliacion_ha IS NULL))
    AND
    (tipo_convenio != 'cop_original' OR tipo_afectacion != 'individual' OR superficie_ampliacion_ha IS NULL)
    AND
    (tipo_convenio NOT IN ('ampliacion', 'ampliacion_remanente') OR superficie_total_ha IS NULL)
    AND
    (tipo_convenio != 'superficie_adicional' OR superficie_real_afectada_ha IS NULL)
    AND
    (tipo_convenio NOT IN ('cop_original', 'obras_complementarias') OR tipo_afectacion != 'colectivo' OR superficie_adicional_ha IS NULL)
)
```

**Justificación**: 
- Garantiza lógicamente que una fila cumpla los requisitos de exclusión sin provocar errores de contradicción matemática (utilizando implicaciones `NOT A OR B`).

**Tabla de Uso**:

| Tipo Afectación | Tipo Convenio | Campo a Usar |
|-----------------|---------------|--------------|
| Individual | COP Original | `superficie_total_ha` |
| Individual | Modificatorio | Ninguno (solo montos) |
| Individual | Ampliación | `superficie_total_ha` (nueva superficie) |
| Individual | Ampliación Remanente | `superficie_total_ha` |
| Colectivo | COP Original | `superficie_real_afectada_ha` |
| Colectivo | Modificatorio | `superficie_real_afectada_ha` |
| Colectivo | Superficie Adicional | `superficie_adicional_ha` |
| Colectivo | Obras Complementarias | `superficie_real_afectada_ha` |

---

### Decisiones de Diseño Relacionadas

#### Resumen de Clarificaciones Críticas

Esta sección documenta decisiones arquitectónicas clave relacionadas con las reglas de negocio implementadas. Dos aspectos críticos requieren especial atención:

**1. Campos de Superficie - Distinción Jurídica**:
- `superficie_total_ha`: EXCLUSIVO para afectaciones INDIVIDUALES (parcelas con titular específico)
- `superficie_real_afectada_ha`: EXCLUSIVO para afectaciones COLECTIVAS (tierras de uso común inalienables)
- Esta distinción no es técnica sino **jurídica**: refleja diferencias legales fundamentales en el derecho agrario mexicano

**2. Ciclo Normalizado de Obras Complementarias**:
- Las Obras Complementarias detonan un nuevo ciclo de asamblea y RAN. En lugar de utilizar campos duplicados con sufijos "_2", el diseño relacional emplea la inserción de nuevos registros en la tabla `asamblea` que se relacionan con los nuevos convenios a través de `id_asamblea_autorizacion`.
- Esto subsana los problemas de normalización inherentes al antiguo sistema en Excel.

**3. Restricciones RAN en Modificatorios Individuales**:
- El Modificatorio Individual (al ser un mero ajuste económico privado sin afectación adicional de superficie) NO requiere inscripción en el RAN, según lo define el proceso (Fase 3B). El diseño exige estrictamente que sus campos registrales queden nulos a través del constraint `chk_modificatorio_individual_restricciones`.

**4. Ubicación Normalizada de "No. de Parcela / Solar"**:
- El número de parcela/solar (cuando aplica a tierras colectivas) describe funcionalmente el "Destino de la Superficie" en la asamblea de Derechos Colectivos (Fase 3A). Se movió lógicamente hacia la tabla `afectacion` junto al campo `destino_superficie`, ya que pertenece puramente a los datos formales de la afectación y no al registro genérico del cruce `tramo_nucleo`.

**5. Trazabilidad Determinista del Quórum (id_padron)**:
- Se añadió explícitamente una llave foránea `id_padron` en la tabla `asamblea`. Aunque el sistema podría derivar el padrón cruzando la fecha de la asamblea con la fecha del padrón, esta llave foránea asegura inmutabilidad jurídica. Hace que cada acta de asamblea esté unida irrefutablemente a una versión histórica del censo de población para probar la legalidad del quórum.

**6. Excepciones Operativas Reforzadas mediante Triggers**:
- Las banderas booleanas para excepciones como `es_expropiacion` y `proyecto_no_afecta_uso_comun` ahora actúan como validadores absolutos en el motor de base de datos a través de *Triggers* automáticos (`fn_validar_convenio_expropiacion`, `fn_validar_afectacion_uso_comun`). Si un tramo-núcleo es forzado a juicio expropiatorio (fracasa el acuerdo), se bloqueará inmediatamente cualquier intento de crear convenios conciliatorios, previniendo estados inconsistentes.

---

#### Nomenclatura de Tipos de Convenio

Se adoptó la convención **snake_case en minúsculas** para todos los valores enum de `tipo_convenio`:
- 'cop_original' (no 'COP' ni 'COP Original')
- 'modificatorio'
- 'superficie_adicional'
- 'obras_complementarias'
- 'ampliacion'
- 'ampliacion_remanente'

**Justificación**: Consistencia con convenciones SQL/PostgreSQL y prevención de errores de tipeo por sensibilidad a mayúsculas.

#### Estado de Convenio - Vista Calculada

En lugar de agregar un campo explícito `estatus` a la tabla `convenio`, se creó la vista `vw_convenio_estado` que calcula el estado basándose en las fechas existentes:
- 'borrador': Ninguna fecha poblada
- 'firmado': `fecha_firma` poblada
- 'ingresado_ran': `ingreso_ran_fecha` poblada
- 'inscrito_ran': `convenio_inscrito_fecha_ran` poblada

**Justificación**: Las fechas son la fuente de verdad del estado del convenio. Mantener un campo separado requeriría sincronización mediante triggers y aumentaría el riesgo de inconsistencias. La vista calculada garantiza que el estado siempre refleje las fechas reales.

#### Normalización del Ciclo de Obras Complementarias

El proceso requiere que Obras Complementarias detone un **nuevo ciclo completo** de asamblea, firmas e inscripción RAN. Según el stakeholder:

> "Al ser una nueva ocupación en tierras de uso común, la ley exige detonar de nuevo todo el ciclo: se requiere una nueva asamblea de anuencia, nuevas firmas y su propia inscripción al Registro Agrario Nacional (RAN)."

**Estrategia Adoptada**: Creación de nuevos registros relacionales
- Se inserta un nuevo registro en la tabla `asamblea` con `contexto_proceso = 'obras_complementarias'`.
- Se inserta un nuevo registro en la tabla `convenio` (tipo_convenio = 'obras_complementarias') vinculado a la nueva asamblea.

**Justificación**: 
- Cumple estrictamente con las reglas de normalización de base de datos.
- Previene la mezcla conceptual entre campos de registro de asamblea y registro de convenio.
- Facilita el mantenimiento y trazabilidad escalable del histórico de afectaciones en un mismo expediente.

**Alternativa Rechazada**: Campos duplicados con sufijo "_2" (e.g. `ingreso_ran_fecha_2`)
- Desventaja: Rompe la Primera Forma Normal.
- Desventaja: Traslada artificialmente las limitaciones bidimensionales de una hoja de cálculo al motor de base de datos.

---

#### Diferencia entre superficie_total_ha y superficie_real_afectada_ha

Según el stakeholder y el documento `Descripción proceso.md`, la distinción es **jurídica** y refleja diferencias fundamentales en el derecho agrario mexicano:

> "Superficie Total Real Afectada (Ha) mide el impacto sobre las tierras inalienables que son de uso comunal y requieren asambleas, mientras que Superficie Total (Ha.) se captura en expedientes privados para medir la afectación de una parcela particular con un dueño específico."

**Regla Implementada**:
- **`superficie_total_ha`**: Se usa SOLO para afectaciones INDIVIDUALES
  - Mide la superficie de una **parcela con titular específico** (ejidatario o comunero identificado)
  - Se captura en **expedientes privados** mediante negociación directa
  - **NO requiere asamblea** - la autorización la da el titular directamente
  - Proceso: Sensibilización → Caminamiento → Negociación privada → Firma
  
- **`superficie_real_afectada_ha`**: Se usa SOLO para afectaciones COLECTIVAS
  - Mide la superficie de **tierras de uso común** del núcleo agrario completo
  - Estas tierras son **inalienables** por ley (no se pueden vender ni transferir)
  - Pertenecen al **núcleo agrario completo**, no a individuos
  - **REQUIERE asamblea** con quórum legal para su afectación
  - Proceso: Sensibilización → Caminamiento → Asamblea anuencia → Firma → RAN

- Validado mediante constraint `chk_superficie_segun_tipo_afectacion`

**Excepción**: Modificatorio Individual no usa ninguno de los dos campos (solo captura montos)

**Justificación**: 
- Refleja la diferencia legal fundamental entre propiedad individual (parcelas) y colectiva (uso común)
- Previene confusión sobre qué campo usar según el tipo de afectación
- Las tierras de uso común son inalienables y requieren proceso de asamblea
- Las parcelas individuales tienen un titular específico y proceso directo
- Facilita reportes separados por tipo de derecho
- Los montos de indemnización y procesos de pago son diferentes según el tipo

**Importancia Operativa**:
- Confundir estos campos genera inconsistencias graves en el seguimiento legal
- Los reportes de liberación deben separar claramente derechos individuales vs colectivos
- Los requisitos documentales ante el RAN son distintos
- El FIFONAFE administra los pagos de forma diferente según el tipo de derecho

---

## Correctness Properties

*Una propiedad es una característica o comportamiento que debe ser cierto en todas las ejecuciones válidas de un sistema—esencialmente, una declaración formal sobre lo que el sistema debe hacer. Las propiedades sirven como puente entre las especificaciones legibles por humanos y las garantías de correctness verificables por máquinas.*

Basándose en el análisis de prework de los 25 requerimientos, se han identificado las siguientes propiedades universales que deben cumplirse. Estas propiedades son adecuadas para property-based testing dado que el sistema gestiona lógica de negocio compleja con reglas de validación, cálculos y relaciones que deben mantenerse consistentes a través de todas las entradas válidas.

### Property 1: Integridad Referencial de Autorizaciones

*Para cualquier* usuario autenticado con un rol específico, los permisos otorgados deben corresponder exactamente a las operaciones permitidas para ese rol: Usuario_Captura debe tener permisos de lectura y escritura, Usuario_Visualizador debe tener solo permisos de lectura, y Administrador debe tener todos los permisos.

**Validates: Requirements 1.2, 1.3**

**Estrategia de Implementación:**
- Generar usuarios aleatorios con roles variados
- Para cada usuario, verificar que `checkPermission()` retorna los valores correctos según el rol
- Validar que intentos de escritura por Usuario_Visualizador sean rechazados

### Property 2: Unicidad de Identificadores de Tramos

*Para cualquier* par de Tramos creados en el sistema, sus identificadores (claves) deben ser únicos—no pueden existir dos Tramos con la misma clave simultáneamente.

**Validates: Requirements 2.1, 2.3**

**Estrategia de Implementación:**
- Generar múltiples Tramos con claves aleatorias
- Verificar que intentar crear un Tramo con clave existente resulte en error
- Validar que la consulta de todos los Tramos no contiene duplicados de clave

### Property 3: Cardinalidad de Relación Tramo-Frente

*Para cualquier* Tramo, el sistema debe permitir la asociación de cero o más Frentes, y cada Frente debe estar asociado exactamente a un Tramo válido.

**Validates: Requirements 2.2, 2.4**

**Estrategia de Implementación:**
- Generar Tramos aleatorios con cantidades variables de Frentes (0 a N)
- Para cada Frente creado, verificar que `tramoId` referencia un Tramo existente
- Validar que eliminar un Tramo elimina sus Frentes asociados (cascada)

### Property 4: Validación Condicional de Afectaciones Individuales

*Para cualquier* Afectación clasificada como Derecho_Individual, el sistema debe requerir y almacenar número de parcela e información del titular; para Afectaciones de Derecho_Colectivo, estos campos deben ser opcionales o nulos.

**Validates: Requirements 4.3, 4.4**

**Estrategia de Implementación:**
- Generar Afectaciones aleatorias de ambos tipos
- Para Derecho_Individual: validar que `numeroParcela` y `nombreTitular` sean requeridos
- Para Derecho_Colectivo: validar que estos campos pueden ser nulos
- Intentar crear Derecho_Individual sin estos campos debe fallar


### Property 5: Cálculo Correcto de Superficies desde Geometrías

*Para cualquier* polígono georreferenciado válido almacenado en PostGIS, el cálculo de superficie en hectáreas y metros cuadrados debe ser consistente y reproducible utilizando funciones espaciales estándar (ST_Area).

**Validates: Requirements 3.3, 4.1**

**Estrategia de Implementación:**
- Generar polígonos aleatorios válidos con diferentes formas y tamaños
- Calcular superficie mediante `ST_Area()` y funciones del sistema
- Verificar que hectáreas = metros cuadrados / 10000
- Validar que recalcular la misma geometría produce el mismo resultado

### Property 6: Conservación de Geometrías en Transformaciones de Coordenadas

*Para cualquier* geometría válida, transformar del sistema de coordenadas A al sistema B y de regreso al sistema A debe producir una geometría equivalente (dentro de un margen de tolerancia por redondeo).

**Validates: Requirements 12.1, 12.2**

**Estrategia de Implementación:**
- Generar geometrías aleatorias en WGS84 (EPSG:4326)
- Transformar a UTM (EPSG:32614 o similar) usando `ST_Transform()`
- Transformar de regreso a WGS84
- Verificar que las coordenadas resultantes difieren por menos de 0.0001 grados

### Property 7: Consistencia de Intersecciones Geométricas

*Para cualquier* par de geometrías A y B, si A intersecta B, entonces B debe intersectar A (propiedad simétrica de intersección).

**Validates: Requirements 12.3, 12.4**

**Estrategia de Implementación:**
- Generar pares aleatorios de Frentes y Núcleos Agrarios
- Si `ST_Intersects(frente, nucleo)` es verdadero, verificar que `ST_Intersects(nucleo, frente)` también es verdadero
- Validar que el área de intersección es consistente sin importar el orden

### Property 8: Validación de Requisitos de Convenio según Tipo

*Para cualquier* Convenio creado, los campos requeridos deben cumplir con las reglas de validación específicas del tipo: COP requiere fecha de anuencia y minuta de asamblea, Modificatorio requiere referencia a COP previo, Superficie_Adicional requiere nueva superficie afectada.

**Validates: Requirements 5.1, 5.2, 5.3, 5.4**

**Estrategia de Implementación:**
- Generar Convenios aleatorios de cada tipo
- Para tipo COP: validar que `fechaAnuencia` y `minutaAsamblea` estén presentes
- Para tipo Modificatorio: validar que `convenioAnteriorId` referencie un COP existente
- Intentar crear Convenio sin campos requeridos debe fallar

### Property 9: Progresión de Estados de Convenio

*Para cualquier* Convenio, la transición de estados debe seguir el flujo válido: Borrador → Firmado → Inscrito_RAN. No se permiten transiciones hacia atrás ni saltos de estados.

**Validates: Requirements 5.5, 8.1**

**Estrategia de Implementación:**
- Generar Convenios en diferentes estados
- Intentar transicionar de Borrador a Inscrito_RAN directamente debe fallar
- Intentar transicionar de Inscrito_RAN a Firmado (regresión) debe fallar
- Validar que solo transiciones válidas (Borrador→Firmado, Firmado→Inscrito_RAN) sean aceptadas

### Property 10: Integridad de Auditoría

*Para cualquier* operación de modificación (INSERT, UPDATE, DELETE) en tablas auditadas, debe existir exactamente un registro correspondiente en la tabla de auditoría con usuario, timestamp y valores anteriores/nuevos correctos.

**Validates: Requirements 11.1, 11.2**

**Estrategia de Implementación:**
- Ejecutar operaciones aleatorias de creación, actualización y eliminación
- Para cada operación, verificar que existe un registro en `auditoria`
- Validar que `usuarioId`, `timestamp`, `operacion` y `valoresAnteriores`/`valoresNuevos` sean correctos
- Verificar que el conteo de registros de auditoría coincide con el conteo de operaciones

### Property 11: Validación de Vigencia de ORV

*Para cualquier* Núcleo Agrario con ORV registrado, el campo calculado `estaVigente` debe ser verdadero si la fecha actual está entre `fechaInicioVigencia` y `fechaFinVigencia`, y falso en caso contrario.

**Validates: Requirement 3.5**

**Estrategia de Implementación:**
- Generar ORVs con diferentes rangos de fechas de vigencia (pasadas, actuales, futuras)
- Para cada ORV, calcular `estaVigente` basado en fecha actual del sistema
- Verificar que el cálculo coincide con la lógica: `fechaActual BETWEEN fechaInicio AND fechaFin`

### Property 12: Consistencia de Superficies Liberadas

*Para cualquier* Núcleo Agrario, la suma de superficies liberadas de todas sus Afectaciones no debe exceder la superficie total afectada del Núcleo.

**Validates: Requirements 4.2, 12.5**

**Estrategia de Implementación:**
- Generar Núcleos Agrarios con múltiples Afectaciones
- Para cada Núcleo, calcular `superficieLiberada = SUM(afectaciones liberadas)`
- Verificar que `superficieLiberada <= superficieTotalAfectada`
- Intentar liberar más superficie de la afectada debe generar advertencia o error

### Property 13: Validación de Excepciones Operativas

*Para cualquier* Núcleo Agrario o Tramo-Núcleo, el sistema debe registrar y hacer cumplir correctamente las banderas de excepciones operativas, tales como Expropiación Directa, Comunidad Indígena y No Afecta Tierras de Uso Común, activando bloqueos de convenios según aplique.

**Validates: Requirements 19.1, 19.2, 19.3, 19.4**

**Estrategia de Implementación:**
- Crear Tramo-Núcleo marcado con `es_expropiacion = true`
- Verificar que los triggers bloquean la creación de convenios conciliatorios
- Verificar que los reportes discriminan correctamente las banderas `comunidad_indigena` y `proyecto_no_afecta_uso_comun`

### Property 14: Trazabilidad de Oficios FIFONAFE

*Para cualquier* proceso de indemnización, el sistema debe garantizar la captura exacta de la cadena interinstitucional de oficios de FIFONAFE con sus fechas y números respectivos.

**Validates: Requirements 9.3, 9.4**

**Estrategia de Implementación:**
- Generar un flujo de indemnización registrando los 4 oficios obligatorios (FIFONAFE, DGAOPR, Representación)
- Verificar que la vista de seguimiento muestre el estado de completitud basado en la integridad de la cadena documental

## Despliegue e Infraestructura

Esta sección detalla la arquitectura de despliegue, configuración de infraestructura, estrategias de alta disponibilidad y respaldos para cumplir con los requerimientos no funcionales RNF-13 (disponibilidad 99%) y RNF-14 (respaldos automáticos diarios).

### Arquitectura de Despliegue

El sistema se despliega en una arquitectura de tres niveles con redundancia y balanceo de carga:

```
┌─────────────────────────────────────────────────────────┐
│              Balanceador de Carga (HAProxy/Nginx)       │
│              - Health checks automáticos                │
│              - Distribución round-robin                 │
│              - Failover automático                      │
└─────────────────────────────────────────────────────────┘
                          ↓
         ┌────────────────┴────────────────┐
         ↓                                  ↓
┌─────────────────┐              ┌─────────────────┐
│ Servidor App 1  │              │ Servidor App 2  │
│ (Node.js/Python)│              │ (Node.js/Python)│
│ - API REST      │              │ - API REST      │
│ - Servicios GIS │              │ - Servicios GIS │
└─────────────────┘              └─────────────────┘
         ↓                                  ↓
         └────────────────┬────────────────┘
                          ↓
         ┌────────────────────────────────┐
         │ PostgreSQL + PostGIS (Primario)│
         │ - Modo replicación streaming   │
         └────────────────────────────────┘
                          ↓
         ┌────────────────────────────────┐
         │ PostgreSQL (Réplica - Standby) │
         │ - Hot standby para lectura     │
         │ - Failover automático          │
         └────────────────────────────────┘
```

### Componentes de Infraestructura

**1. Servidores de Aplicación (Mínimo 2 instancias)**
- **Especificación**: 4 vCPU, 8 GB RAM, 50 GB SSD
- **Sistema Operativo**: Linux (Ubuntu Server 22.04 LTS o similar)
- **Runtime**: Node.js 18+ o Python 3.10+
- **Configuración**: Modo cluster con gestión de procesos (PM2 para Node.js, Gunicorn/uWSGI para Python)
- **Redundancia**: Mínimo 2 instancias activas para disponibilidad 99%

**2. Balanceador de Carga**
- **Tecnología**: HAProxy o Nginx
- **Funcionalidades**:
  - Health checks HTTP cada 10 segundos
  - Timeout de conexión: 5 segundos
  - Failover automático si servidor no responde
  - Distribución de carga: Round-robin con sticky sessions (para sesiones JWT)
- **Alta Disponibilidad**: Configuración activo-pasivo con Keepalived (VIP compartida)

**3. Base de Datos PostgreSQL + PostGIS**
- **Especificación Primario**: 8 vCPU, 16 GB RAM, 500 GB SSD (con capacidad de expansión)
- **Especificación Réplica**: Igual que primario
- **Versión**: PostgreSQL 14+ con PostGIS 3.3+
- **Configuración de Alta Disponibilidad**:
  - Replicación streaming síncrona o asíncrona
  - Hot standby habilitado para réplica de lectura
  - Failover automático con herramientas como Patroni, repmgr o pgpool-II
  - WAL archiving para recuperación point-in-time

**4. Almacenamiento de Archivos**
- **Ubicación**: Almacenamiento compartido (NFS, S3-compatible, o similar)
- **Propósito**: Documentos escaneados, archivos geoespaciales, reportes generados
- **Respaldo**: Sincronización con almacenamiento secundario

### Estrategia de Alta Disponibilidad (RNF-13)

**Objetivo**: Disponibilidad del 99% durante horario laboral (8:00 AM - 8:00 PM)

**Cálculo de Tiempo de Inactividad Permitido**:
- Horario laboral: 12 horas/día
- 99% disponibilidad = máximo 1% de downtime
- Downtime permitido: ~7.2 minutos por día laboral

**Mecanismos de Alta Disponibilidad**:

1. **Redundancia de Servidores de Aplicación**
   - Mínimo 2 instancias activas simultáneamente
   - Balanceador distribuye carga entre instancias saludables
   - Si una instancia falla, el balanceador la marca como inactiva y redirige tráfico

2. **Failover Automático de Base de Datos**
   - PostgreSQL réplica en hot standby
   - Herramienta de failover automático (Patroni recomendado):
     - Detecta falla del primario mediante health checks (cada 10 segundos)
     - Promueve réplica a primario automáticamente
     - Actualiza endpoint de conexión o DNS
     - Tiempo de failover objetivo: < 30 segundos

3. **Health Checks y Monitoreo**
   - Endpoint `/health` en API que verifica:
     - Conectividad con base de datos
     - Uso de memoria y CPU dentro de límites
     - Servicios críticos operativos
   - Balanceador consulta `/health` cada 10 segundos
   - Servidor no saludable se remueve de pool automáticamente

4. **Mantenimiento sin Downtime**
   - Despliegue rolling: actualizar una instancia a la vez
   - Servidor en mantenimiento se marca como drenando (no acepta nuevas conexiones)
   - Conexiones existentes se completan antes de apagar servidor

### Estrategia de Respaldos (RNF-14)

**Objetivo**: Respaldos automáticos diarios con capacidad de recuperación

**Tipo de Respaldos**:

1. **Respaldo Completo Diario (Full Backup)**
   - **Frecuencia**: Diario a las 2:00 AM (fuera de horario laboral)
   - **Método**: `pg_dump` o `pg_basebackup` de PostgreSQL
   - **Contenido**: 
     - Base de datos completa incluyendo esquemas, datos, geometrías
     - Archivos de configuración del sistema
     - Documentos y archivos asociados
   - **Ubicación**: Servidor de respaldos dedicado o almacenamiento en la nube
   - **Retención**: 
     - Respaldos diarios: 7 días
     - Respaldos semanales: 4 semanas
     - Respaldos mensuales: 12 meses

2. **Respaldo Incremental Continuo (WAL Archiving)**
   - **Frecuencia**: Continuo (cada vez que se completa un segmento WAL)
   - **Método**: PostgreSQL WAL archiving con `archive_command`
   - **Propósito**: Permite recuperación point-in-time (PITR)
   - **Ubicación**: Almacenamiento separado del servidor principal
   - **Retención**: 30 días de archivos WAL

**Procedimiento de Respaldo Automatizado**:

```bash
#!/bin/bash
# Script de respaldo diario (cron: 0 2 * * *)

BACKUP_DIR="/backups/postgresql"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="sistema_liberacion_derechos"
RETENTION_DAYS=7

# Crear respaldo con pg_dump
pg_dump -U postgres -Fc $DB_NAME > $BACKUP_DIR/backup_$DATE.dump

# Comprimir archivos de documentos
tar -czf $BACKUP_DIR/documentos_$DATE.tar.gz /var/app/documentos

# Eliminar respaldos antiguos
find $BACKUP_DIR -name "backup_*.dump" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "documentos_*.tar.gz" -mtime +$RETENTION_DAYS -delete

# Verificar integridad del respaldo
pg_restore --list $BACKUP_DIR/backup_$DATE.dump > /dev/null
if [ $? -eq 0 ]; then
  echo "Respaldo exitoso: backup_$DATE.dump"
  # Opcional: copiar a almacenamiento remoto (S3, rsync, etc.)
  # aws s3 cp $BACKUP_DIR/backup_$DATE.dump s3://bucket-respaldos/
else
  echo "ERROR: Respaldo falló validación"
  # Enviar alerta a administradores
fi
```

**Procedimiento de Recuperación**:

1. **Recuperación desde Respaldo Completo**:
   ```bash
   # Restaurar base de datos
   pg_restore -U postgres -d $DB_NAME -c $BACKUP_DIR/backup_YYYYMMDD.dump
   
   # Restaurar archivos de documentos
   tar -xzf $BACKUP_DIR/documentos_YYYYMMDD.tar.gz -C /var/app/
   ```

2. **Recuperación Point-in-Time (PITR)**:
   - Restaurar respaldo base más reciente
   - Aplicar archivos WAL hasta el punto de tiempo deseado
   - PostgreSQL replay automático de transacciones

**Verificación de Respaldos**:
- Prueba mensual de restauración en ambiente de prueba
- Validación de integridad mediante `pg_restore --list`
- Monitoreo de tamaño de respaldos (alerta si crece inusualmente o no crece)

### Monitoreo y Alertas

**Herramientas de Monitoreo**:
- **Prometheus + Grafana**: Métricas de sistema, aplicación y base de datos
- **PostgreSQL Exporter**: Métricas específicas de PostgreSQL
- **Node Exporter / Python metrics**: Métricas de servidores de aplicación

**Métricas Clave a Monitorear**:

1. **Disponibilidad**:
   - Uptime de servidores de aplicación
   - Uptime de base de datos primaria
   - Tasa de éxito de health checks
   - Latencia de respuesta de API

2. **Rendimiento**:
   - Tiempo de respuesta de endpoints (p50, p95, p99)
   - Throughput de requests por segundo
   - Duración de consultas SQL
   - Uso de conexiones de base de datos

3. **Recursos**:
   - Uso de CPU, memoria, disco de cada servidor
   - Espacio disponible en base de datos
   - Tamaño de archivos WAL no archivados
   - Lag de replicación (réplica vs primario)

4. **Respaldos**:
   - Éxito/fallo de respaldos diarios
   - Tamaño de respaldos generados
   - Tiempo de ejecución de respaldos
   - Espacio disponible en almacenamiento de respaldos

**Alertas Configuradas**:

| Condición | Severidad | Acción |
|-----------|-----------|--------|
| Servidor de aplicación no responde por > 1 minuto | Crítica | Email + SMS a administradores |
| Base de datos primaria no responde | Crítica | Failover automático + notificación |
| Uso de disco > 85% | Alta | Email a administradores |
| Respaldo diario falló | Alta | Email a administradores |
| Lag de replicación > 5 minutos | Media | Email a administradores |
| Tiempo de respuesta p95 > 3 segundos | Media | Email a desarrolladores |
| Uso de CPU > 80% por > 10 minutos | Media | Email a administradores |

### Consideraciones de Seguridad en Infraestructura

1. **Red y Firewall**:
   - Base de datos no expuesta a internet público
   - Acceso a BD solo desde servidores de aplicación
   - Reglas de firewall restrictivas (whitelist)
   - Conexiones cifradas con TLS/SSL

2. **Acceso y Autenticación**:
   - Acceso SSH mediante claves, sin contraseñas
   - Usuarios con privilegios mínimos necesarios
   - Rotación periódica de credenciales de base de datos

3. **Cifrado**:
   - Conexiones HTTPS para tráfico web (certificado TLS)
   - Cifrado en tránsito para replicación de BD
   - Cifrado en reposo para respaldos (opcional pero recomendado)

### Escalabilidad Futura

El diseño permite escalar horizontalmente según crezca la demanda:

1. **Escalar Capa de Aplicación**:
   - Agregar más instancias de servidores de aplicación
   - Actualizar configuración del balanceador

2. **Escalar Base de Datos**:
   - Agregar réplicas de lectura adicionales
   - Distribuir consultas de solo lectura a réplicas
   - Particionar tablas grandes por fecha o región (si es necesario)

3. **Optimización de Rendimiento**:
   - Caché de consultas frecuentes (Redis/Memcached)
   - CDN para assets estáticos del frontend
   - Índices adicionales basados en patrones de uso real


## Gestión de Sesiones y Autenticación (RNF-9)

Esta sección detalla la implementación del cierre automático de sesión por inactividad, complementando el Módulo de Autenticación y Autorización descrito anteriormente.

### Estrategia de Tokens JWT con Expiración

**Configuración de Tokens**:
- **Access Token**: Token JWT de corta duración para autenticación de requests
  - Tiempo de vida: 30 minutos
  - Contiene: `userId`, `role`, `username`, `iat` (issued at), `exp` (expiration)
  - Almacenado en: memoria del cliente (variable JavaScript), NO en localStorage
  
- **Refresh Token**: Token de larga duración para renovar access tokens
  - Tiempo de vida: 7 días
  - Almacenado en: Cookie HTTPOnly, Secure, SameSite
  - Permite renovar access token sin reautenticación

### Implementación de Inactividad (30 minutos - RNF-9)

**Mecanismo de Detección de Actividad**:

El sistema considera "actividad" cualquiera de las siguientes acciones del usuario:
- Interacción con la interfaz (clicks, tipeo, scroll)
- Peticiones HTTP a la API
- Movimiento del mouse (registrado con throttling para evitar sobrecarga)

**Implementación en Frontend**:

```typescript
class SessionManager {
  private lastActivityTimestamp: number
  private inactivityTimeout: number = 30 * 60 * 1000  // 30 minutos en milisegundos
  private checkInterval: number = 60 * 1000  // Verificar cada minuto
  private intervalId: number | null = null
  
  constructor() {
    this.lastActivityTimestamp = Date.now()
    this.setupActivityListeners()
    this.startInactivityCheck()
  }
  
  // Registrar actividad del usuario
  private setupActivityListeners(): void {
    const events = ['mousedown', 'keypress', 'scroll', 'touchstart']
    events.forEach(event => {
      window.addEventListener(event, () => this.updateActivity(), { passive: true })
    })
  }
  
  private updateActivity(): void {
    this.lastActivityTimestamp = Date.now()
  }
  
  // Verificar periódicamente si hay inactividad
  private startInactivityCheck(): void {
    this.intervalId = window.setInterval(() => {
      const inactiveTime = Date.now() - this.lastActivityTimestamp
      
      if (inactiveTime >= this.inactivityTimeout) {
        this.handleInactivityTimeout()
      } else if (inactiveTime >= this.inactivityTimeout - 5 * 60 * 1000) {
        // Advertencia 5 minutos antes del cierre
        this.showInactivityWarning(this.inactivityTimeout - inactiveTime)
      }
    }, this.checkInterval)
  }
  
  private handleInactivityTimeout(): void {
    // Limpiar intervalo
    if (this.intervalId) clearInterval(this.intervalId)
    
    // Invalidar token en servidor
    this.logout()
    
    // Redirigir a login con mensaje
    window.location.href = '/login?reason=inactivity'
  }
  
  private showInactivityWarning(timeRemaining: number): void {
    // Mostrar notificación al usuario
    const minutes = Math.floor(timeRemaining / 60000)
    alert(`Tu sesión expirará en ${minutes} minuto(s) por inactividad. ¿Deseas continuar?`)
    // Si usuario hace click en "Continuar", updateActivity() se llama automáticamente
  }
  
  private async logout(): Promise<void> {
    await fetch('/api/auth/logout', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${this.getAccessToken()}` }
    })
    // Limpiar tokens locales
    this.clearTokens()
  }
}
```

**Implementación en Backend**:

```typescript
// Middleware para actualizar timestamp de última actividad
function trackActivity(req: Request, res: Response, next: NextFunction) {
  if (req.user) {
    // Actualizar timestamp en sesión o base de datos
    sessionStore.updateLastActivity(req.user.userId, new Date())
  }
  next()
}

// Aplicar middleware a todas las rutas protegidas
app.use('/api/*', authenticateJWT, trackActivity)
```

### Renovación Automática de Tokens

Para evitar interrupciones durante sesiones activas, el sistema implementa renovación automática de access tokens:

**Flujo de Renovación**:

1. **Detección de Expiración Próxima**:
   - Cliente verifica tiempo de expiración del access token antes de cada request
   - Si el token expira en menos de 5 minutos, solicita renovación

2. **Endpoint de Renovación**:
   ```typescript
   // POST /api/auth/refresh
   async function refreshToken(req: Request, res: Response) {
     const refreshToken = req.cookies.refreshToken
     
     if (!refreshToken) {
       return res.status(401).json({ error: 'No refresh token provided' })
     }
     
     try {
       // Validar refresh token
       const decoded = jwt.verify(refreshToken, REFRESH_TOKEN_SECRET)
       
       // Verificar que no esté en lista negra (opcional)
       const isBlacklisted = await checkTokenBlacklist(refreshToken)
       if (isBlacklisted) {
         return res.status(401).json({ error: 'Token revoked' })
       }
       
       // Generar nuevo access token
       const newAccessToken = jwt.sign(
         { userId: decoded.userId, role: decoded.role, username: decoded.username },
         ACCESS_TOKEN_SECRET,
         { expiresIn: '30m' }
       )
       
       // Actualizar timestamp de actividad
       await sessionStore.updateLastActivity(decoded.userId, new Date())
       
       return res.json({ accessToken: newAccessToken })
     } catch (error) {
       return res.status(401).json({ error: 'Invalid refresh token' })
     }
   }
   ```

3. **Cliente Solicita Renovación Automáticamente**:
   ```typescript
   async function apiRequest(endpoint: string, options: RequestInit) {
     const token = getAccessToken()
     
     // Verificar si token está por expirar
     if (isTokenExpiringSoon(token)) {
       await renewAccessToken()
     }
     
     // Realizar request con token actualizado
     return fetch(endpoint, {
       ...options,
       headers: {
         ...options.headers,
         'Authorization': `Bearer ${getAccessToken()}`
       }
     })
   }
   ```

### Cierre de Sesión Manual

El usuario puede cerrar sesión manualmente en cualquier momento:

**Endpoint de Logout**:
```typescript
// POST /api/auth/logout
async function logout(req: Request, res: Response) {
  const userId = req.user.userId
  const token = req.headers.authorization?.split(' ')[1]
  
  // Agregar token a lista negra (opcional, para invalidación inmediata)
  await addTokenToBlacklist(token, 30 * 60)  // Expira en 30 minutos
  
  // Eliminar refresh token de base de datos
  await sessionStore.deleteRefreshToken(userId)
  
  // Limpiar cookie de refresh token
  res.clearCookie('refreshToken')
  
  return res.status(200).json({ message: 'Logout successful' })
}
```

### Almacenamiento de Sesiones

**Opción 1: Stateless (solo JWT, sin almacenamiento de sesión)**
- Ventaja: Escalable, sin dependencia de almacenamiento compartido
- Desventaja: No se puede invalidar token hasta que expire naturalmente

**Opción 2: Almacenamiento de Refresh Tokens en Base de Datos (Recomendado)**
- Tabla `sesiones_activas`:
  ```sql
  CREATE TABLE sesiones_activas (
     id_sesion SERIAL PRIMARY KEY,
     id_usuario INTEGER NOT NULL REFERENCES usuario(id_usuario) ON DELETE CASCADE,
     refresh_token_hash VARCHAR(255) NOT NULL,
     ultima_actividad TIMESTAMPTZ NOT NULL,
     fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
     direccion_ip VARCHAR(45),
     user_agent TEXT,
     UNIQUE(refresh_token_hash)
   );
   
   CREATE INDEX idx_sesiones_usuario ON sesiones_activas(id_usuario);
  ```

- Ventajas:
  - Permite invalidar sesiones inmediatamente
  - Auditoría de sesiones activas
  - Permite listar y cerrar sesiones remotamente
  - Limpieza automática de sesiones expiradas:
    ```sql
    -- Job diario para eliminar sesiones inactivas
    DELETE FROM sesiones_activas 
    WHERE ultima_actividad < NOW() - INTERVAL '30 minutes';
    ```

### Casos Especiales de Gestión de Sesiones

**1. Múltiples Sesiones del Mismo Usuario**:
- El sistema permite múltiples sesiones concurrentes (mismo usuario en diferentes dispositivos/navegadores)
- Cada sesión tiene su propio refresh token
- Cerrar sesión en un dispositivo no afecta otras sesiones

**2. Cierre de Sesión Remoto**:
- Administradores pueden cerrar sesiones de otros usuarios desde panel de administración
- Implementación:
  ```typescript
  async function revokeUserSessions(adminUserId: string, targetUserId: string) {
    // Verificar que adminUserId tiene rol Administrador
    // Eliminar todos los refresh tokens del usuario objetivo
    await sessionStore.deleteAllUserSessions(targetUserId)
    // Los access tokens actuales seguirán funcionando hasta expirar (máximo 30 minutos)
  }
  ```

**3. Cambio de Rol o Permisos**:
- Si se modifica el rol de un usuario, las sesiones activas mantienen el rol anterior hasta que el access token expire
- Para aplicar cambios inmediatamente, se puede forzar cierre de sesiones del usuario

**4. Cambio de Contraseña**:
- Al cambiar contraseña, se invalidan todas las sesiones existentes
- Usuario debe autenticarse nuevamente con la nueva contraseña


## Consideraciones Técnicas Adicionales

### Clarificación sobre Geometrías de Tramos (Req 2.6)

**Inconsistencia Aparente**:
- El requerimiento Req 2.6 menciona "información del polígono del tramo"
- El diseño implementa geometrías lineales (LINESTRING) para Tramos

**Justificación de la Decisión de Diseño**:

Los Tramos representan trazos ferroviarios, que son inherentemente entidades lineales (vías de tren). La implementación con geometría lineal (LINESTRING) es correcta por las siguientes razones:

1. **Naturaleza del Dominio**: Un trazo ferroviario es una línea, no un área
2. **Cálculo de Derecho de Vía**: El área afectada se calcula aplicando un buffer a la línea central (por ejemplo, 50 metros a cada lado)
3. **Representación Cartográfica**: Los trazos ferroviarios se representan como líneas en mapas
4. **Precisión Topológica**: LINESTRING permite representar exactamente la ruta del trazo

**Interpretación del Requerimiento**:
- "Polígono del tramo" se refiere al área de derecho de vía (calculada dinámicamente mediante buffer)
- La geometría base almacenada es lineal
- El "polígono" se genera cuando se necesita calcular intersecciones con núcleos agrarios:
  ```sql
  -- Generar polígono de derecho de vía a partir de línea
  SELECT ST_Buffer(
    ST_Transform(geometria_linea, 32614),  -- Transformar a UTM para buffer en metros
    50  -- Radio del buffer en metros (ancho de derecho de vía)
  ) AS poligono_derecho_via
   FROM tramo
   WHERE id_tramo = 'tramo_id';
  ```

**Recomendación**:
- Mantener geometría lineal (LINESTRING) como representación base
- Calcular polígono de derecho de vía dinámicamente cuando se requiera
- Documentar el ancho de derecho de vía como parámetro configurable del sistema

### Optimización de Consultas Geoespaciales

**Índices Espaciales**:
Todos los campos de geometría deben tener índices GiST para acelerar consultas espaciales:

```sql
CREATE INDEX idx_tramo_geometria ON tramo USING GIST(geometria_linea);
CREATE INDEX idx_frente_geometria ON frente USING GIST(geometria_linea);
CREATE INDEX idx_nucleo_geometria ON nucleo_agrario USING GIST(geometria_poligono);
CREATE INDEX idx_tramo_nucleo_segmento ON tramo_nucleo USING GIST(geometria_segmento);
```

**Simplificación de Geometrías para Visualización**:
Para mejorar rendimiento en mapas con zoom alejado, se puede usar simplificación de Douglas-Peucker:

```sql
-- Simplificar geometría según nivel de zoom
SELECT 
  id, 
  nombre,
  CASE 
    WHEN :zoom_level < 10 THEN ST_Simplify(geometria_poligono, 0.01)
    WHEN :zoom_level < 13 THEN ST_Simplify(geometria_poligono, 0.001)
    ELSE geometria_poligono
  END AS geometria
FROM nucleo_agrario;
```

### Manejo de Sistemas de Coordenadas

**SRIDs Soportados**:
- **EPSG:4326 (WGS84)**: Sistema de coordenadas geográficas estándar para almacenamiento y visualización web
- **EPSG:32614 (UTM Zona 14N)**: Para México central, usado en documentos jurídicos
- **EPSG:32615 (UTM Zona 15N)**: Para México oriental
- **EPSG:32613 (UTM Zona 13N)**: Para México occidental

**Detección Automática de Zona UTM**:
```sql
-- Función para determinar zona UTM basada en longitud
CREATE OR REPLACE FUNCTION detectar_zona_utm(longitud DECIMAL)
RETURNS INTEGER AS $$
BEGIN
  -- Fórmula: zona = floor((longitud + 180) / 6) + 1
  RETURN FLOOR((longitud + 180) / 6) + 1;
END;
$$ LANGUAGE plpgsql IMMUTABLE;
```


## Error Handling

El sistema implementa una estrategia integral de manejo de errores en todas las capas de la arquitectura.

### Clasificación de Errores

**1. Errores de Validación (4xx)**:
- **400 Bad Request**: Datos de entrada inválidos o incompletos
- **401 Unauthorized**: Autenticación fallida o token inválido
- **403 Forbidden**: Usuario autenticado pero sin permisos para la operación
- **404 Not Found**: Recurso solicitado no existe
- **409 Conflict**: Violación de restricciones de unicidad o integridad

**2. Errores de Servidor (5xx)**:
- **500 Internal Server Error**: Error inesperado en lógica de aplicación
- **502 Bad Gateway**: Error de conectividad con base de datos o servicios externos
- **503 Service Unavailable**: Sistema en mantenimiento o sobrecargado

### Estructura de Respuestas de Error

Todas las respuestas de error siguen un formato JSON consistente:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Los datos proporcionados son inválidos",
    "details": [
      {
        "field": "numeroEjidatarios",
        "message": "Debe ser un número positivo",
        "value": -5
      }
    ],
    "timestamp": "2024-01-15T10:30:00Z",
    "requestId": "req_abc123"
  }
}
```

### Códigos de Error del Dominio

| Código | Descripción | HTTP Status |
|--------|-------------|-------------|
| `AUTH_FAILED` | Credenciales inválidas | 401 |
| `TOKEN_EXPIRED` | Token JWT expirado | 401 |
| `INSUFFICIENT_PERMISSIONS` | Usuario sin permisos | 403 |
| `RESOURCE_NOT_FOUND` | Entidad no encontrada | 404 |
| `DUPLICATE_KEY` | Identificador duplicado | 409 |
| `VALIDATION_ERROR` | Datos inválidos | 400 |
| `GEOMETRY_INVALID` | Geometría topológicamente inválida | 400 |
| `SRID_MISMATCH` | Sistema de coordenadas incompatible | 400 |
| `WORKFLOW_VIOLATION` | Transición de estado inválida | 409 |
| `REFERENTIAL_INTEGRITY` | Violación de integridad referencial | 409 |
| `DATABASE_ERROR` | Error de base de datos | 500 |
| `GIS_CALCULATION_ERROR` | Error en cálculo geoespacial | 500 |

### Manejo de Errores por Capa

**Capa de Presentación (Frontend)**:
```typescript
class ErrorHandler {
  static handleApiError(error: ApiError): void {
    switch (error.code) {
      case 'TOKEN_EXPIRED':
        // Intentar renovar token automáticamente
        this.refreshToken().catch(() => {
          // Si falla renovación, redirigir a login
          window.location.href = '/login?reason=session_expired'
        })
        break
      
      case 'INSUFFICIENT_PERMISSIONS':
        // Mostrar mensaje de permisos insuficientes
        this.showNotification('No tienes permisos para realizar esta operación', 'error')
        break
      
      case 'VALIDATION_ERROR':
        // Resaltar campos con errores en formulario
        this.highlightFieldErrors(error.details)
        break
      
      case 'GEOMETRY_INVALID':
        // Mostrar errores de geometría en mapa
        this.showGeometryErrors(error.details)
        break
      
      default:
        // Error genérico
        this.showNotification('Ocurrió un error inesperado', 'error')
        this.logError(error)
    }
  }
}
```

**Capa de Aplicación (Backend)**:
```typescript
// Middleware global de manejo de errores
function errorHandlerMiddleware(
  error: Error, 
  req: Request, 
  res: Response, 
  next: NextFunction
): void {
  // Log del error para debugging
  logger.error({
    message: error.message,
    stack: error.stack,
    requestId: req.id,
    userId: req.user?.userId,
    path: req.path,
    method: req.method
  })
  
  // Determinar respuesta según tipo de error
  if (error instanceof ValidationError) {
    return res.status(400).json({
      error: {
        code: 'VALIDATION_ERROR',
        message: error.message,
        details: error.validationDetails,
        timestamp: new Date().toISOString(),
        requestId: req.id
      }
    })
  }
  
  if (error instanceof GeometryError) {
    return res.status(400).json({
      error: {
        code: 'GEOMETRY_INVALID',
        message: error.message,
        details: error.geometryErrors,
        timestamp: new Date().toISOString(),
        requestId: req.id
      }
    })
  }
  
  if (error instanceof DatabaseError) {
    // No exponer detalles internos de BD al cliente
    return res.status(500).json({
      error: {
        code: 'DATABASE_ERROR',
        message: 'Error interno del servidor',
        timestamp: new Date().toISOString(),
        requestId: req.id
      }
    })
  }
  
  // Error genérico no manejado
  return res.status(500).json({
    error: {
      code: 'INTERNAL_ERROR',
      message: 'Error interno del servidor',
      timestamp: new Date().toISOString(),
      requestId: req.id
    }
  })
}
```

**Capa de Datos (Base de Datos)**:
```sql
-- Manejo de errores en funciones PL/pgSQL
CREATE OR REPLACE FUNCTION calcular_superficie_liberada(p_id_tramo_nucleo INTEGER)
RETURNS DECIMAL AS $$
DECLARE
  superficie DECIMAL;
BEGIN
  -- Intentar cálculo
  SELECT COALESCE(SUM(a.superficie_afectada_ha), 0)
  INTO superficie
  FROM afectacion a
  JOIN convenio c ON a.id_afectacion = c.id_afectacion
    AND a.id_tramo_nucleo = c.id_tramo_nucleo
  WHERE c.id_tramo_nucleo = p_id_tramo_nucleo
    AND c.convenio_inscrito_fecha_ran IS NOT NULL;
  
  RETURN superficie;
  
EXCEPTION
  WHEN OTHERS THEN
    -- Log del error
    INSERT INTO error_log (funcion, mensaje, sqlstate, timestamp)
    VALUES ('calcular_superficie_liberada', SQLERRM, SQLSTATE, NOW());
    
    -- Re-lanzar error para que aplicación lo maneje
    RAISE;
END;
$$ LANGUAGE plpgsql;
```

### Estrategias Específicas de Recuperación

**1. Errores de Conectividad de Base de Datos**:
- **Estrategia**: Reintentos con backoff exponencial
- **Implementación**:
  ```typescript
  async function executeWithRetry<T>(
    operation: () => Promise<T>,
    maxRetries: number = 3,
    baseDelay: number = 1000
  ): Promise<T> {
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        return await operation()
      } catch (error) {
        if (attempt === maxRetries - 1) throw error
        
        // Verificar si es error recuperable
        if (!isRecoverableError(error)) throw error
        
        // Esperar antes de reintentar (backoff exponencial)
        const delay = baseDelay * Math.pow(2, attempt)
        await sleep(delay)
      }
    }
  }
  ```

**2. Errores de Validación de Geometrías**:
- **Estrategia**: Intentar reparación automática con ST_MakeValid
- **Implementación**:
  ```sql
  -- Intentar corregir geometría inválida
  CREATE OR REPLACE FUNCTION guardar_geometria_segura(
    entidad_id INTEGER,
    geometria GEOMETRY
  ) RETURNS GEOMETRY AS $$
  DECLARE
    geometria_valida GEOMETRY;
  BEGIN
    -- Verificar validez
    IF ST_IsValid(geometria) THEN
      RETURN geometria;
    ELSE
      -- Intentar reparación
      geometria_valida := ST_MakeValid(geometria);
      
      IF ST_IsValid(geometria_valida) THEN
        -- Log de advertencia
        INSERT INTO advertencias_geometria (entidad_id, mensaje, timestamp)
        VALUES (entidad_id, 'Geometría corregida automáticamente', NOW());
        
        RETURN geometria_valida;
      ELSE
        -- Si no se puede reparar, rechazar
        RAISE EXCEPTION 'Geometría inválida y no reparable';
      END IF;
    END IF;
  END;
  $$ LANGUAGE plpgsql;
  ```

**3. Timeouts de Consultas Largas**:
- **Configuración**: Timeout de consulta a nivel de base de datos
  ```sql
  -- Configurar timeout global
  ALTER DATABASE sistema_liberacion_derechos SET statement_timeout = '30s';
  
  -- Timeout específico para consultas geoespaciales complejas
  SET statement_timeout = '60s';
  ```
- **Manejo en aplicación**: Detectar timeout y ofrecer opciones al usuario (simplificar consulta, exportar en background)

**4. Violaciones de Integridad Referencial**:
- **Estrategia**: Transacciones con verificación previa
- **Implementación**:
  ```typescript
  async function eliminarTramo(idTramo: number): Promise<void> {
    const transaction = await db.transaction()
    
    try {
      // Verificar dependencias antes de eliminar
      const frentesAsociados = await transaction.query(
        'SELECT COUNT(*) FROM frente WHERE id_tramo = $1',
        [idTramo]
      )
      
      if (frentesAsociados.rows[0].count > 0) {
        throw new Error('No se puede eliminar tramo con frentes asociados')
      }
      
      // Proceder con eliminación
      await transaction.query('DELETE FROM tramo WHERE id_tramo = $1', [idTramo])
      await transaction.commit()
    } catch (error) {
      await transaction.rollback()
      throw error
    }
  }
  ```

### Logging y Monitoreo de Errores

**Niveles de Log**:
- **ERROR**: Errores que impiden completar operaciones
- **WARN**: Situaciones anómalas pero recuperables
- **INFO**: Operaciones exitosas importantes
- **DEBUG**: Información detallada para debugging

**Campos de Log Estándar**:
```typescript
interface LogEntry {
  level: 'ERROR' | 'WARN' | 'INFO' | 'DEBUG'
  timestamp: string
  requestId: string
  userId?: string
  message: string
  context: {
    service: string
    operation: string
    [key: string]: any
  }
  error?: {
    message: string
    stack: string
    code?: string
  }
}
```

**Integración con Sistema de Monitoreo**:
- Errores 5xx activan alertas automáticas
- Tasa de errores 4xx monitoreada para detectar problemas de usabilidad
- Dashboard de errores con tendencias y análisis


## Testing Strategy

El sistema implementa una estrategia de testing integral en múltiples niveles para garantizar correctness, confiabilidad y mantenibilidad.

### Pirámide de Testing

```
                    ┌─────────────┐
                    │   E2E Tests │  (10%)
                    │  Manuales   │
                    └─────────────┘
                  ┌─────────────────┐
                  │ Integration Tests│  (20%)
                  │   Automatizados  │
                  └─────────────────┘
              ┌─────────────────────────┐
              │    Unit Tests            │  (40%)
              │    Automatizados         │
              └─────────────────────────┘
          ┌───────────────────────────────────┐
          │   Property-Based Tests            │  (30%)
          │   (Verificación de Propiedades)   │
          └───────────────────────────────────┘
```

### 1. Property-Based Testing (PBT)

**Objetivo**: Verificar que las propiedades de correctness definidas se cumplen para todas las entradas válidas posibles.

**Framework**: Utilizar bibliotecas especializadas:
- **JavaScript/TypeScript**: fast-check
- **Python**: Hypothesis

**Ejemplo de Test de Propiedad**:

```typescript
import fc from 'fast-check'

describe('Property 1: Integridad Referencial de Autorizaciones', () => {
  it('Usuario_Captura debe tener permisos de lectura y escritura', () => {
    fc.assert(
      fc.property(
        // Generador de usuarios con rol Usuario_Captura
        fc.record({
          userId: fc.nat(),
          username: fc.string(),
          role: fc.constant('operador')
        }),
        // Generador de recursos
        fc.oneof(
          fc.constant('Tramo'),
          fc.constant('Frente'),
          fc.constant('NucleoAgrario'),
          fc.constant('Afectacion')
        ),
        async (user, resource) => {
          // Verificar permisos de lectura
          const canRead = await authService.checkPermission(
            user.userId,
            resource,
            'read'
          )
          expect(canRead).toBe(true)
          
          // Verificar permisos de escritura
          const canWrite = await authService.checkPermission(
            user.userId,
            resource,
            'write'
          )
          expect(canWrite).toBe(true)
        }
      ),
      { numRuns: 100 }  // Ejecutar 100 casos aleatorios
    )
  })
  
  it('Usuario_Visualizador debe tener solo permisos de lectura', () => {
    fc.assert(
      fc.property(
        fc.record({
          userId: fc.nat(),
          username: fc.string(),
          role: fc.constant('analista')
        }),
        fc.oneof(
          fc.constant('Tramo'),
          fc.constant('Frente'),
          fc.constant('NucleoAgrario')
        ),
        async (user, resource) => {
          const canRead = await authService.checkPermission(
            user.userId,
            resource,
            'read'
          )
          expect(canRead).toBe(true)
          
          const canWrite = await authService.checkPermission(
            user.userId,
            resource,
            'write'
          )
          expect(canWrite).toBe(false)
        }
      ),
      { numRuns: 100 }
    )
  })
})
```

**Generadores Personalizados para el Dominio**:

```typescript
// Generador de geometrías lineales válidas
const lineStringGenerator = fc.array(
  fc.tuple(
    fc.double({ min: -180, max: 180 }),  // longitud
    fc.double({ min: -90, max: 90 })      // latitud
  ),
  { minLength: 2, maxLength: 100 }
).map(coords => ({
  type: 'LineString',
  coordinates: coords
}))

// Generador de polígonos válidos (cerrados)
const polygonGenerator = fc.array(
  fc.tuple(
    fc.double({ min: -180, max: 180 }),
    fc.double({ min: -90, max: 90 })
  ),
  { minLength: 3, maxLength: 50 }
).map(coords => {
  // Cerrar el polígono (primer punto = último punto)
  const closedCoords = [...coords, coords[0]]
  return {
    type: 'Polygon',
    coordinates: [closedCoords]
  }
})

// Generador de Convenios
const convenioGenerator = fc.record({
  tipo: fc.oneof(
    fc.constant('COP'),
    fc.constant('Modificatorio'),
    fc.constant('Superficie_Adicional'),
    fc.constant('Obras_Complementarias'),
    fc.constant('Ampliacion'),
    fc.constant('Ampliacion_Remanente')
  ),
  fechaFirma: fc.date({ min: new Date('2020-01-01'), max: new Date() }),
  monto90: fc.option(fc.double({ min: 0, max: 10000000 })),
  monto100: fc.option(fc.double({ min: 0, max: 10000000 })),
  montoBDT: fc.option(fc.double({ min: 0, max: 5000000 }))
})
```

### 2. Unit Testing

**Objetivo**: Verificar que componentes individuales funcionan correctamente de forma aislada.

**Cobertura Objetivo**: Mínimo 80% de cobertura de código

**Áreas de Enfoque**:
- Validaciones de datos
- Funciones de transformación y cálculo
- Lógica de negocio pura (sin dependencias externas)

**Ejemplo de Unit Test**:

```typescript
describe('GISService.calcularSuperficie', () => {
  it('debe calcular superficie correctamente para polígono cuadrado', async () => {
    // Polígono cuadrado de 100m x 100m en UTM
    const poligono = {
      type: 'Polygon',
      coordinates: [[
        [500000, 2000000],
        [500100, 2000000],
        [500100, 2000100],
        [500000, 2000100],
        [500000, 2000000]
      ]]
    }
    
    const resultado = await gisService.calcularSuperficie(poligono)
    
    expect(resultado.metrosCuadrados).toBeCloseTo(10000, 1)
    expect(resultado.hectareas).toBeCloseTo(1, 4)
  })
  
  it('debe manejar geometrías nulas correctamente', async () => {
    await expect(
      gisService.calcularSuperficie(null)
    ).rejects.toThrow('Geometría no puede ser nula')
  })
})

describe('MotorCalculosGeoService.calcularPorcentajeAvanceFrente', () => {
  let mockDb: jest.Mocked<Database>
  let service: MotorCalculosGeoService
  
  beforeEach(() => {
    mockDb = createMockDatabase()
    service = new MotorCalculosGeoService(mockDb)
  })
  
  it('debe calcular 100% cuando toda superficie está liberada', async () => {
    // Mock de datos
    mockDb.query.mockResolvedValueOnce({
      rows: [{ superficie_total: 100, superficie_liberada: 100 }]
    })
    
    const resultado = await service.calcularPorcentajeAvanceFrente('frente-1')
    
    expect(resultado.porcentajeTotal).toBe(100)
    expect(resultado.colorIndicador).toBe('verde')
  })
  
  it('debe calcular 0% cuando no hay superficie liberada', async () => {
    mockDb.query.mockResolvedValueOnce({
      rows: [{ superficie_total: 100, superficie_liberada: 0 }]
    })
    
    const resultado = await service.calcularPorcentajeAvanceFrente('frente-1')
    
    expect(resultado.porcentajeTotal).toBe(0)
    expect(resultado.colorIndicador).toBe('rojo')
  })
})
```

### 3. Integration Testing

**Objetivo**: Verificar que componentes funcionan correctamente cuando se integran entre sí.

**Áreas de Enfoque**:
- Interacción entre capa de aplicación y base de datos
- Flujos completos de API endpoints
- Cálculos geoespaciales con PostGIS real
- Transformaciones de coordenadas

**Configuración de Ambiente de Prueba**:
- Base de datos PostgreSQL + PostGIS dedicada para tests
- Datos de prueba predefinidos (fixtures)
- Limpieza automática entre tests

**Ejemplo de Integration Test**:

```typescript
describe('API Integration: Gestión de Núcleos Agrarios', () => {
  let testDb: Database
  let apiClient: TestApiClient
  let authToken: string
  
  beforeAll(async () => {
    // Inicializar BD de prueba
    testDb = await setupTestDatabase()
    await testDb.runMigrations()
    
    // Autenticar usuario de prueba
    authToken = await apiClient.login('test_usuario', 'password')
  })
  
  afterAll(async () => {
    await testDb.cleanup()
  })
  
  it('debe crear núcleo agrario con geometría y calcular superficie', async () => {
    const nucleoData = {
      nombre: 'Ejido Prueba',
      tipo: 'Ejido',
      estado: 'Jalisco',
      municipio: 'Guadalajara',
      geometriaPoligono: {
        type: 'Polygon',
        coordinates: [[
          [-103.35, 20.67],
          [-103.34, 20.67],
          [-103.34, 20.68],
          [-103.35, 20.68],
          [-103.35, 20.67]
        ]]
      }
    }
    
    const response = await apiClient.post(
      '/api/nucleos-agrarios',
      nucleoData,
      { headers: { Authorization: `Bearer ${authToken}` } }
    )
    
    expect(response.status).toBe(201)
    expect(response.data.id).toBeDefined()
    expect(response.data.superficieHectareas).toBeGreaterThan(0)
    
    // Verificar que se guardó en BD
    const nucleoEnBD = await testDb.query(
      'SELECT * FROM nucleo_agrario WHERE id_nucleo = $1',
      [response.data.id]
    )
    expect(nucleoEnBD.rows).toHaveLength(1)
    expect(ST_IsValid(nucleoEnBD.rows[0].geometria_poligono)).toBe(true)
  })
  
  it('debe calcular intersecciones correctamente con frentes', async () => {
    // Crear frente que intersecta núcleo
    const frenteId = await createTestFrente(testDb, {
      geometriaLinea: {
        type: 'LineString',
        coordinates: [
          [-103.355, 20.675],
          [-103.345, 20.675]
        ]
      }
    })
    
    // Solicitar intersecciones
    const response = await apiClient.get(
      `/api/motor-calculos/intersecciones/frente/${frenteId}`,
      { headers: { Authorization: `Bearer ${authToken}` } }
    )
    
    expect(response.status).toBe(200)
    expect(response.data).toHaveLength(1)
    expect(response.data[0].nucleoAgrarioNombre).toBe('Ejido Prueba')
    expect(response.data[0].superficieInterseccionHa).toBeGreaterThan(0)
  })
})
```

### 4. End-to-End (E2E) Testing

**Objetivo**: Verificar flujos completos del usuario desde interfaz hasta base de datos.

**Framework**: Playwright o Cypress

**Áreas de Enfoque**:
- Flujos críticos de usuario
- Interacción con mapas interactivos
- Formularios complejos
- Navegación entre vistas

**Ejemplo de E2E Test**:

```typescript
describe('E2E: Creación de Convenio COP', () => {
  let page: Page
  
  beforeEach(async () => {
    page = await browser.newPage()
    await page.goto('http://localhost:3000/login')
    
    // Login
    await page.fill('[name="username"]', 'usuario_captura')
    await page.fill('[name="password"]', 'password')
    await page.click('button[type="submit"]')
    await page.waitForURL('**/dashboard')
  })
  
  it('debe permitir crear convenio COP con todos los campos requeridos', async () => {
    // Navegar a formulario de convenio
    await page.click('text=Convenios')
    await page.click('text=Nuevo Convenio')
    
    // Seleccionar tipo
    await page.selectOption('[name="tipo"]', 'COP')
    
    // Llenar campos requeridos para COP
    await page.fill('[name="fechaAnuencia"]', '2024-01-15')
    await page.fill('[name="minutaAsamblea"]', 'Acta 001/2024')
    await page.fill('[name="fechaFirma"]', '2024-02-01')
    await page.fill('[name="monto90"]', '500000')
    
    // Seleccionar núcleo agrario de dropdown
    await page.click('[name="nucleoAgrarioId"]')
    await page.click('text=Ejido San José')
    
    // Guardar
    await page.click('button:has-text("Guardar")')
    
    // Verificar éxito
    await expect(page.locator('.notification-success')).toBeVisible()
    await expect(page.locator('.notification-success')).toContainText(
      'Convenio creado exitosamente'
    )
    
    // Verificar que aparece en lista
    await page.click('text=Lista de Convenios')
    await expect(page.locator('td:has-text("Acta 001/2024")')).toBeVisible()
  })
  
  it('debe validar campos requeridos antes de guardar', async () => {
    await page.click('text=Convenios')
    await page.click('text=Nuevo Convenio')
    await page.selectOption('[name="tipo"]', 'COP')
    
    // Intentar guardar sin llenar campos requeridos
    await page.click('button:has-text("Guardar")')
    
    // Verificar mensajes de error
    await expect(page.locator('.error-fechaAnuencia')).toContainText(
      'Fecha de anuencia es requerida'
    )
    await expect(page.locator('.error-minutaAsamblea')).toContainText(
      'Minuta de asamblea es requerida'
    )
  })
})

describe('E2E: Interacción con Mapa', () => {
  it('debe permitir dibujar polígono de núcleo agrario en mapa', async () => {
    const page = await browser.newPage()
    await loginAsGeografo(page)
    
    // Navegar a crear núcleo agrario
    await page.click('text=Núcleos Agrarios')
    await page.click('text=Nuevo Núcleo')
    
    // Activar herramienta de dibujo
    await page.click('[data-testid="draw-polygon-tool"]')
    
    // Simular clicks en el mapa para dibujar polígono
    const map = await page.locator('#map-container')
    await map.click({ position: { x: 200, y: 200 } })
    await map.click({ position: { x: 300, y: 200 } })
    await map.click({ position: { x: 300, y: 300 } })
    await map.click({ position: { x: 200, y: 300 } })
    await map.click({ position: { x: 200, y: 200 } })  // Cerrar polígono
    
    // Confirmar geometría
    await page.click('button:has-text("Confirmar Geometría")')
    
    // Verificar que se calculó superficie automáticamente
    const superficieInput = page.locator('[name="superficieHectareas"]')
    await expect(superficieInput).toHaveValue(/^\d+\.\d+$/)
    
    // Completar formulario y guardar
    await page.fill('[name="nombre"]', 'Ejido Prueba Dibujado')
    await page.selectOption('[name="tipo"]', 'Ejido')
    await page.click('button:has-text("Guardar")')
    
    // Verificar que aparece en mapa
    await expect(map.locator('[data-nucleo-id]')).toBeVisible()
  })
})
```

### 5. Performance Testing

**Objetivo**: Verificar que el sistema cumple con requerimientos de rendimiento (RNF-1, RNF-2, RNF-3).

**Herramientas**: Apache JMeter, k6, Artillery

**Escenarios de Prueba**:

1. **Carga de Usuario Concurrente** (RNF-1: 50 usuarios simultáneos):
   ```javascript
   // k6 load test
   import http from 'k6/http'
   import { check, sleep } from 'k6'
   
   export const options = {
     stages: [
       { duration: '2m', target: 50 },  // Ramp up a 50 usuarios
       { duration: '5m', target: 50 },  // Mantener 50 usuarios
       { duration: '2m', target: 0 }    // Ramp down
     ],
     thresholds: {
       http_req_duration: ['p(95)<3000'],  // 95% requests < 3s
       http_req_failed: ['rate<0.01']      // < 1% de errores
     }
   }
   
   export default function() {
     const token = login()
     
     // Simular navegación típica
     http.get('https://api.example.com/nucleos-agrarios', {
       headers: { Authorization: `Bearer ${token}` }
     })
     
     sleep(2)
     
     http.get('https://api.example.com/tramos', {
       headers: { Authorization: `Bearer ${token}` }
     })
     
     sleep(3)
   }
   ```

2. **Consultas Geoespaciales Complejas** (RNF-2: < 5 segundos):
   - Intersección de frente con múltiples núcleos agrarios
   - Cálculo de superficies liberadas para tramo completo
   - Generación de reportes con datos geográficos

3. **Carga de Mapas con Muchas Geometrías** (RNF-3: < 2 segundos):
   - Cargar 500+ polígonos de núcleos agrarios
   - Verificar tiempo de renderizado en frontend
   - Medir impacto de simplificación de geometrías

**Criterios de Aceptación**:
- 95% de requests < 3 segundos
- 99% de requests < 5 segundos
- 0% de errores bajo carga normal
- < 1% de errores bajo carga máxima

### 6. Security Testing

**Objetivo**: Verificar que el sistema es seguro contra vulnerabilidades comunes.

**Áreas de Prueba**:

1. **Autenticación y Autorización**:
   - Intentar acceder a recursos sin autenticación
   - Intentar realizar operaciones sin permisos suficientes
   - Verificar expiración de tokens
   - Verificar cierre de sesión por inactividad

2. **Inyección SQL**:
   - Intentar inyecciones en todos los campos de entrada
   - Verificar uso de consultas parametrizadas
   - Ejemplo de test:
     ```typescript
     it('debe prevenir inyección SQL en búsqueda de núcleos', async () => {
       const maliciousInput = "'; DROP TABLE nucleo_agrario; --"
       
       const response = await apiClient.get(
         `/api/nucleos-agrarios/buscar?nombre=${maliciousInput}`
       )
       
       // No debe generar error de SQL
       expect(response.status).not.toBe(500)
       
       // Verificar que tabla sigue existiendo
       const count = await testDb.query(
         'SELECT COUNT(*) FROM nucleo_agrario'
       )
       expect(count.rows[0].count).toBeGreaterThan(0)
     })
     ```

3. **Cross-Site Scripting (XSS)**:
   - Intentar inyectar scripts en campos de texto
   - Verificar sanitización de inputs
   - Verificar escape de outputs

4. **Cross-Site Request Forgery (CSRF)**:
   - Verificar tokens CSRF en formularios
   - Verificar validación de origen de requests

**Herramientas**:
- OWASP ZAP para escaneo automático de vulnerabilidades
- Burp Suite para pruebas manuales
- npm audit / pip-audit para dependencias vulnerables

### 7. Accessibility Testing

**Objetivo**: Verificar que la interfaz es accesible para usuarios con discapacidades.

**Estándares**: WCAG 2.1 Level AA

**Herramientas**:
- axe DevTools
- Lighthouse (Chrome DevTools)
- NVDA/JAWS screen readers

**Áreas de Verificación**:
- Contraste de colores (mínimo 4.5:1)
- Navegación por teclado
- Atributos ARIA correctos
- Etiquetas de formulario
- Texto alternativo para imágenes

### Test Data Management

**Fixtures de Datos de Prueba**:

```typescript
// fixtures/nucleos-agrarios.ts
export const nucleosAgrariosFixtures = [
  {
    id_nucleo: 1,
    id_municipio: 1,
    nombre_nucleo: 'Ejido San José',
    tipo_nucleo: 'ejido',
    comunidad_indigena: false,
    geometriaPoligono: {
      type: 'MultiPolygon',
      coordinates: [[[[
        [-103.35, 20.67],
        [-103.34, 20.67],
        [-103.34, 20.68],
        [-103.35, 20.68],
        [-103.35, 20.67]
      ]]]]
    }
  },
  // ... más fixtures
]

// Helper para cargar fixtures en BD de prueba
export async function loadFixtures(db: Database) {
  await db.query('TRUNCATE TABLE nucleo_agrario CASCADE')
  
  for (const nucleo of nucleosAgrariosFixtures) {
    await db.query(
      `INSERT INTO nucleo_agrario (id_nucleo, id_municipio, nombre_nucleo, tipo_nucleo, comunidad_indigena, geometria_poligono)
       VALUES ($1, $2, $3, $4, $5, ST_GeomFromGeoJSON($6))`,
      [nucleo.id_nucleo, nucleo.id_municipio, nucleo.nombre_nucleo, nucleo.tipo_nucleo,
       nucleo.comunidad_indigena, JSON.stringify(nucleo.geometriaPoligono)]
    )
  }
}
```

### Continuous Integration (CI)

**Pipeline de CI**:

```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgis/postgis:14-3.3
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run unit tests
        run: npm run test:unit
      
      - name: Run property-based tests
        run: npm run test:property
      
      - name: Run integration tests
        run: npm run test:integration
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
      
      - name: Check code coverage
        run: npm run test:coverage
        
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
      
      - name: Run linter
        run: npm run lint
      
      - name: Run security audit
        run: npm audit --audit-level=moderate
```

### Test Execution Schedule

| Tipo de Test | Frecuencia | Duración Estimada | Trigger |
|--------------|-----------|-------------------|---------|
| Unit Tests | Cada commit | 2-5 minutos | CI automático |
| Property-Based Tests | Cada commit | 5-10 minutos | CI automático |
| Integration Tests | Cada commit | 10-15 minutos | CI automático |
| E2E Tests | Cada PR | 20-30 minutos | CI automático |
| Performance Tests | Semanal | 30-60 minutos | Programado |
| Security Tests | Semanal | 15-30 minutos | Programado |
| Accessibility Tests | Cada release | 15-30 minutos | Manual |

### Test Metrics y Reporting

**Métricas Clave**:
- **Code Coverage**: Objetivo > 80%
- **Test Pass Rate**: Objetivo > 99%
- **Test Execution Time**: Monitorear tendencias
- **Flaky Tests**: Identificar y corregir tests intermitentes

**Reporting**:
- Dashboard de cobertura (Codecov, Coveralls)
- Reportes de tests en PRs
- Tendencias históricas de métricas
- Alertas automáticas si métricas caen por debajo de umbrales
