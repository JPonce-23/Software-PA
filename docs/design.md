# Documento de Diseño Técnico

## Overview

Este documento presenta el diseño técnico de un sistema web multiusuario para el seguimiento del proceso de liberación de derechos de vía de proyectos ferroviarios que afectan propiedad social (ejidos y comunidades) en México. El sistema reemplaza el actual seguimiento basado en Excel, proporcionando gestión centralizada de datos, control de acceso basado en roles, tableros de control en tiempo real, visualización geográfica interactiva y capacidades completas de reporteo.

> **Estado y autoridad del documento.** La fuente funcional es `flujograma
> propiedad social.pdf`, resumida en `Descripción proceso.md`; el esquema
> ejecutable se determina exclusivamente por las migraciones aplicadas. Este
> documento conserva ejemplos conceptuales e históricos de una etapa anterior
> —incluidos fragmentos con `Frente`, contratos TypeScript y pruebas
> hipotéticas— que no describen necesariamente el código vigente. Para el
> Corte 2 sólo son normativas las secciones marcadas como diseño objetivo y el
> alcance de `ESTADO_PROYECTO.md`; los ejemplos históricos no deben copiarse ni
> ejecutarse.

El alcance funcional actual es exclusivamente propiedad social, tanto
derechos colectivos como individuales. No se modela la gestión de propiedad
privada, catastro, Registro Público de la Propiedad, juicio expropiatorio ni
procesos propios de otras instituciones.

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
- **Proyectos**: Contenedores de los tramos ferroviarios
- **Tramos**: Segmentos principales del proyecto ferroviario con representación geométrica (líneas)
- **Tramo_Núcleo**: Cruce de un tramo con un núcleo agrario y expediente maestro territorial
- **Núcleos Agrarios**: Ejidos y comunidades (entidades de propiedad social) afectados por el proyecto, representados como polígonos georreferenciados
- **Afectaciones**: Subexpedientes confirmados, colectivos o individuales, dentro de un Tramo_Núcleo

**Procesos Documentales:**
- **Sensibilización**: Reuniones de concientización con las comunidades
- **Caminamientos**: Inspecciones técnicas de campo
- **Asambleas**: Reuniones formales de ejidatarios/comuneros para aprobar convenios
- **Convenios**: Acuerdos legales de ocupación de terreno. Los tipos varían según el derecho afectado: para colectivos (COP, Modificatorio, Superficie Adicional, Obras Complementarias) y para individuales (COP, Modificatorio, Ampliación, Ampliación Remanente)
- **Inscripción RAN**: Proceso de registro en el Registro Agrario Nacional
- **FIFONAFE**: Proceso de pago de indemnizaciones a través del fideicomiso

**Análisis Geoespacial:**
- **Intersecciones Geométricas**: Análisis de cruces y afectaciones mediante geometrías de Tramo, Tramo_Núcleo, Núcleo Agrario y Afectación
- **Transformación de Coordenadas**: Conversión entre WGS84 (visualización web) y UTM (documentos jurídicos)
- **Cálculo de Superficies**: Determinación automática de hectáreas y metros cuadrados afectados
- **Validación Topológica**: Verificación de geometrías válidas sin auto-intersecciones

**Actores del Sistema:**
- **Administradores**: Gestionan usuarios y configuración del sistema
- **Usuarios de Captura**: Registran y actualizan información del proceso
- **Geógrafos**: Capturan y editan geometrías de Tramos, Tramo_Núcleo, Núcleos Agrarios y Afectaciones
- **Usuarios Visualizadores**: Consultan reportes, tableros de progreso y mapas interactivos

### Contexto del Dominio

#### Flujo de Proceso Integrado

El sistema sigue el proceso operativo descrito en `Descripción proceso.md`,
fuente funcional canónica. `tramo_nucleo` es el expediente maestro territorial
que articula la investigación, sensibilización, caminamiento y seguimiento
global de la liberación en el cruce. La afectación se registra después, cuando
esa investigación confirma el derecho afectado y ya se conocen su superficie,
geometría y sujetos; cada registro abre un subexpediente operativo.

La navegación objetivo es:

```text
Proyecto → Tramo → Tramo_Núcleo (expediente maestro)
                         └── Afectación (subexpediente)
```

El expediente maestro conserva los antecedentes compartidos. Cada
subexpediente presenta los que le aplican junto con sus actuaciones
específicas, sin duplicar ni trasladar automáticamente la información común.

**Fase 1: Configuración e investigación territorial**
- Selección de Proyecto, Tramo, Tramo_Núcleo y Núcleo Agrario
- Identificación y análisis de posibles afectaciones dentro del expediente
  maestro, sin crear todavía subexpedientes
- Control de ORV (Órganos de Representación y Vigilancia): Verificación de vigencia de autoridades
- Control de Padrón: Número de ejidatarios/comuneros para cálculo de quórum
- Documentación soporte y excepciones (Comunidad Indígena, Expropiación Directa)

**Fase 2: Acercamiento, campo y confirmación**
- **Sensibilización**: Reuniones informativas con el núcleo agrario
- **Caminamiento**: Inspecciones técnicas que delimitan superficie, geometría,
  sujetos y BDT
- **Afectación confirmada**: Su registro abre un subexpediente operativo
- Cada subexpediente se **bifurca** según el tipo de derecho:

**Fase 3A: Matriz de Derechos Colectivos (Uso Común)**
- **COP Original**: Asamblea de anuencia → Firma → Inscripción RAN (acta y convenio)
- **Modificatorio**: Ajustes al COP original (montos, superficie)
- **Superficie Adicional**: Nueva asamblea + nuevo ciclo RAN para superficie descubierta posteriormente
- **Obras Complementarias**: **Nuevo contexto completo** con las etapas aplicables, modelado mediante registros independientes y preservando intacto el COP original

**Fase 3B: Matriz de Derechos Individuales (Parcelas)**
- **COP Original**: Negociación directa con el titular → Firma → Inscripción RAN
- **Modificatorio Individual**: Solo ajuste de montos (sin superficie ni BDT)
- **Ampliación**: Nueva superficie afectada de la misma parcela
- **Ampliación Remanente**: Superficie remanente de ampliación

**Fase 4: Matriz FIFONAFE e Informes de No Conflictos**
- Cadena de oficios interinstitucionales (FIFONAFE ↔ DGAOPR ↔ PA)
- Seguimiento independiente para afectaciones colectivas e individuales
- Pago de la indemnización aplicable
- **Liberado** se deriva después del pago; la inscripción ante el RAN sólo
  representa avance registral

**Salidas terminales fuera del seguimiento ordinario**
- **Expropiación directa**: se registra el supuesto y se detiene el flujo
  gestionado por la PA
- **Comunidad indígena**: se registra el supuesto y se detiene el flujo
  gestionado por la PA
- La salida puede abarcar todo el expediente maestro o sólo una afectación.
  En este último caso las demás afectaciones continúan y el agregado se
  presenta como mixto.

**Puntos Críticos del Flujo**:
1. Las tierras de uso común (colectivas) son **inalienables** - requieren asamblea obligatoriamente
2. Las parcelas individuales tienen titular específico - negociación directa sin asamblea
3. Obras Complementarias es un convenio variante que requiere **nuevo ciclo completo** (no es modificación)
4. Los campos RAN "_2" del Excel original representan un segundo ciclo operativo y se normalizan como registros independientes de Asamblea y Convenio, evitando conservar columnas paralelas en una misma fila del expediente

### Arquitectura de Alto Nivel

El sistema sigue una arquitectura de tres capas con extensiones geoespaciales:

```
┌──────────────────────────────────────────────────────┐
│            Capa de Presentación                      │
│   (Aplicación Web Responsiva - React 19)              │
│   - Mapa Interactivo (Leaflet.js)                    │
│   - Herramientas de Dibujo Geográfico                │
│   - Paneles de Información Contextual                │
│   - Tableros de Control                              │
└──────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────┐
│            Capa de Aplicación                        │
│  (REST API - Python/FastAPI)                         │
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

**DA-9: Rastreabilidad Total del Borrado Lógico (Soft Deletes)**
- **Decisión**: Queda prohibida la eliminación física de registros. Además del campo `activo BOOLEAN`, todas las tablas operativas asumen tener la traza de baja (`fecha_baja`, `id_usuario_baja`, `motivo_baja`) y la de reactivación (`fecha_reactivacion`, `id_usuario_reactivacion`, `motivo_reactivacion`).
- **Justificación**: El trigger `fn_validar_baja_logica()` bloquea bajas anónimas y conserva el historial al reactivarse. Además rige la regla "Soft-Restrict" impidiendo baja de padres con hijos activos.

**DA-10: Auditoría Transaccional y Usuario de Migración**
- **Decisión**: El trigger `fn_audit_log` rechaza cualquier cambio si el contexto `app.current_user_id` es nulo.
- **Justificación**: Para scripts de base de datos directos, se define el usuario `id_usuario = 1` (SYSTEM_MIGRATION). Se debe invocar estrictamente de forma transaccional: `BEGIN; SET LOCAL "app.current_user_id" = '1'; [DML]; COMMIT;`.

**DA-11: Cálculo Geoespacial Oficial vs Visualización (Buffers)**
- **Decisión**: La columna `ancho_total_derecho_via_m` se define en metros. La base de datos usa `ST_Buffer(geom::geography)` para validación topológica `ST_Intersects` al vuelo. Sin embargo, para cálculos de superficie oficial (`ST_Area`), se requiere forzar transformación a UTM (`ST_Transform`).


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
  rol: 'admin' | 'operador' | 'visualizador' | 'geografo'
}

interface Usuario {
  id_usuario: number // PK SERIAL
  nombre: string
  apellido_paterno: string
  apellido_materno: string | null
  correo: string
  rol: 'admin' | 'operador' | 'visualizador' | 'geografo'
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

### Módulo de Gestión Territorial (Proyecto, Tramo y Tramo_Núcleo)

```typescript
interface TerritorialService {
  getTramoById(id_tramo: number): Promise<Tramo>
  listTramos(): Promise<Tramo[]>
  getTramoNucleoIntersect(id_tramo: number, id_nucleo: number): Promise<TramoNucleo>
}

interface Proyecto {
  id_proyecto: number
  clave_proyecto: string
  nombre_proyecto: string
  descripcion: string | null
  activo: boolean
}

interface UsuarioTramo {
  id_usuario: number
  id_tramo: number
  fecha_asignacion: string
  activo: boolean
  motivo_reactivacion: string | null
}

interface Tramo {
  id_tramo: number // PK SERIAL
  id_proyecto: number // FK a Proyecto
  clave_tramo: string
  nombre_tramo: string
  descripcion: string | null
  geometria_linea: GeoJSON | null
  activo: boolean
  fecha_registro: Date
  observaciones: string | null
}

interface TramoNucleo {
  id_tramo_nucleo: number // PK SERIAL
  id_tramo: number // FK a Tramo
  id_nucleo: number // FK a NucleoAgrario
  consecutivo: number
  numero_tramo: string | null
  geometria_segmento: GeoJSON | null
  longitud_m: number | null
  es_expropiacion: boolean
  causa_problema: string | null
  proyecto_no_afecta_uso_comun: boolean | null
  activo: boolean
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
  activo: boolean
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
   * Se captura en expedientes individuales de propiedad social mediante negociación directa con el titular.
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
    Proyecto 1 ─── N Tramo
    Tramo 1 ─── N Tramo_Núcleo
    Núcleo_Agrario 1 ─── N Tramo_Núcleo
    Tramo_Núcleo 1 ─── N Afectación
    Usuario N ─── M Tramo, mediante usuario_tramo

    entidad_federativa ||--o{ municipio : "tiene"
    municipio ||--o{ nucleo_agrario : "contiene"
    
    usuario ||--o{ bitacora : "registra_auditoria"
    usuario ||--o{ usuario_tramo : "asignado_a"
    tramo ||--o{ usuario_tramo : "asignado_a"
    
    proyecto ||--|{ tramo : "contiene"
    
    %% Optimización de cruce espacial
    tramo ||--o{ tramo_nucleo : "cruza"
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

El diagrama anterior distingue la estructura física vigente de la experiencia
funcional objetivo. Algunas entidades de antecedentes, como
`actividad_campo`, conservan actualmente su llave hacia `tramo_nucleo`. Esto
es consistente con su papel como expediente maestro. En el Corte 2 los
antecedentes compartidos deben permanecer en ese nivel y ser consultables
desde las afectaciones a las que apliquen; sólo las actuaciones exclusivas
deben vincularse directamente con un subexpediente concreto.

### Entidades de Base de Datos

El esquema SQL ejecutable y vigente se mantiene exclusivamente en:

- `backend/db/migrations/001_init_schema.sql`, como línea base.
- `backend/db/migrations/002_apply_audit_fixes.sql`, como correcciones de
  integridad y auditoría.
- `backend/db/migrations/003_add_proyecto_drop_frente.sql`, que incorpora
  Proyecto y retira Frente.
- `backend/db/migrations/004_adaptaciones_fase2.sql`, que agrega las
  adaptaciones estructurales posteriores.

Este documento describe decisiones de arquitectura; no es fuente ejecutable del esquema.

### Vistas de Base de Datos

Las vistas ejecutables deben consultarse en las migraciones aplicadas. Los
fragmentos SQL que siguen son referencias históricas: los ejemplos de
`vw_tramo_nucleo_estado` y `vw_dashboard_liberacion` todavía contienen
`id_frente` y equiparan inscripción ante el RAN con liberación, por lo que no
representan el diseño objetivo ni deben ejecutarse.

**Vista: vw_convenio_estado**
Calcula el estado del flujo de trabajo de cada convenio basado en fechas clave.

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
    (c.convenio_inscrito_fecha_ran IS NOT NULL) AS esta_inscrito_ran,
    (c.fecha_firma IS NOT NULL) AS esta_firmado
FROM convenio c WHERE c.activo = TRUE;
```

**Vista: vw_orv_estado**
```sql
CREATE OR REPLACE VIEW vw_orv_estado AS
SELECT 
    *,
    (CURRENT_DATE BETWEEN inicio_vigencia AND fin_vigencia) AS orv_vigente 
FROM orv WHERE activo = TRUE;
```

**Vista: vw_tramo_nucleo_estado**
Evalúa en tiempo real si un cruce geográfico ya tiene convenios, trámites, o problemas documentados. Separa el estado legal del geoespacial.
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
    EXISTS (SELECT 1 FROM asamblea a WHERE a.id_tramo_nucleo = tn.id_tramo_nucleo AND a.resultado_anuencia = 'otorgada' AND a.activo = TRUE) AS tiene_anuencia,
    EXISTS (SELECT 1 FROM convenio c WHERE c.id_tramo_nucleo = tn.id_tramo_nucleo AND c.convenio_inscrito_fecha_ran IS NOT NULL AND c.activo = TRUE) AS tiene_convenio_inscrito_ran,
    -- ESTADO LEGAL
    CASE
        WHEN tn.es_expropiacion = TRUE THEN 'problema'
        WHEN NULLIF(BTRIM(tn.causa_problema), '') IS NOT NULL THEN 'problema'
        WHEN (SELECT COUNT(*) FROM afectacion a WHERE a.id_tramo_nucleo = tn.id_tramo_nucleo AND a.activo = TRUE) > 0 
             AND NOT EXISTS (
                 SELECT 1 FROM afectacion a WHERE a.id_tramo_nucleo = tn.id_tramo_nucleo AND a.activo = TRUE
                 AND NOT EXISTS (SELECT 1 FROM convenio c WHERE c.id_afectacion = a.id_afectacion AND c.convenio_inscrito_fecha_ran IS NOT NULL AND c.activo = TRUE)
             ) THEN 'liberado'
        WHEN EXISTS (SELECT 1 FROM convenio c WHERE c.id_tramo_nucleo = tn.id_tramo_nucleo AND c.activo = TRUE) THEN 'en_proceso'
        ELSE 'pendiente'
    END AS estado_legal,
    -- ESTADO GEOESPACIAL
    CASE
        WHEN (SELECT COUNT(*) FROM afectacion a WHERE a.id_tramo_nucleo = tn.id_tramo_nucleo AND a.activo = TRUE) = 0 THEN 'pendiente_digitalizacion'
        WHEN EXISTS (SELECT 1 FROM afectacion a WHERE a.id_tramo_nucleo = tn.id_tramo_nucleo AND a.geometria_afectacion IS NULL AND a.activo = TRUE) THEN 'pendiente_digitalizacion'
        ELSE 'completo'
    END AS estado_geoespacial
FROM tramo_nucleo tn WHERE tn.activo = TRUE;
```

**Vista: vw_dashboard_liberacion**
Agrupa las afectaciones, convenios y estatus para análisis global. Resuelve la precedencia de los modificatorios y restringe la liberación a convenios inscritos.
```sql
CREATE OR REPLACE VIEW vw_dashboard_liberacion AS
WITH ModificatoriosVigentes AS (
    SELECT id_convenio_padre, id_convenio, superficie_real_afectada_ha, superficie_total_ha
    FROM (
        SELECT id_convenio_padre, id_convenio, superficie_real_afectada_ha, superficie_total_ha,
               ROW_NUMBER() OVER (PARTITION BY id_convenio_padre ORDER BY fecha_firma DESC, id_convenio DESC) as rn
        FROM convenio
        WHERE tipo_convenio = 'modificatorio' AND convenio_inscrito_fecha_ran IS NOT NULL AND activo = TRUE
    ) t WHERE rn = 1
),
ConveniosBase AS (
    SELECT c.id_tramo_nucleo,
           c.id_convenio,
           c.tipo_afectacion,
           COALESCE(m.superficie_real_afectada_ha, m.superficie_total_ha, c.superficie_real_afectada_ha, c.superficie_total_ha, 0) AS superficie_liberada_ha
    FROM convenio c
    LEFT JOIN ModificatoriosVigentes m ON m.id_convenio_padre = c.id_convenio
    WHERE c.tipo_convenio IN ('cop_original', 'obras_complementarias')
      AND c.convenio_inscrito_fecha_ran IS NOT NULL
      AND c.activo = TRUE
),
SuperficiesAdicionales AS (
    SELECT c.id_tramo_nucleo,
           c.id_convenio,
           c.tipo_afectacion,
           COALESCE(m.superficie_real_afectada_ha, m.superficie_total_ha, c.superficie_adicional_ha, c.superficie_ampliacion_ha, 0) AS superficie_liberada_ha
    FROM convenio c
    LEFT JOIN ModificatoriosVigentes m ON m.id_convenio_padre = c.id_convenio
    WHERE c.tipo_convenio IN ('superficie_adicional', 'ampliacion', 'ampliacion_remanente')
      AND c.convenio_inscrito_fecha_ran IS NOT NULL
      AND c.activo = TRUE
),
LiberacionUnificada AS (
    SELECT * FROM ConveniosBase
    UNION ALL
    SELECT * FROM SuperficiesAdicionales
),
AgrupacionLiberada AS (
    SELECT id_tramo_nucleo,
           SUM(superficie_liberada_ha) AS superficie_liberada_ha,
           COUNT(DISTINCT id_convenio) AS total_convenios_formalizados_ran,
           COUNT(DISTINCT CASE WHEN tipo_afectacion = 'colectivo' THEN id_convenio END) AS total_convenios_colectivos_formalizados_ran,
           COUNT(DISTINCT CASE WHEN tipo_afectacion = 'individual' THEN id_convenio END) AS total_convenios_individuales_formalizados_ran,
           SUM(CASE WHEN tipo_afectacion = 'colectivo' THEN superficie_liberada_ha ELSE 0 END) AS total_colectivo_ha,
           SUM(CASE WHEN tipo_afectacion = 'individual' THEN superficie_liberada_ha ELSE 0 END) AS total_individual_ha
    FROM LiberacionUnificada
    GROUP BY id_tramo_nucleo
)
SELECT
    v.id_tramo_nucleo,
    t.id_tramo,
    t.clave_tramo,
    f.id_frente,
    n.id_nucleo,
    n.nombre_nucleo,
    ef.nombre AS entidad_federativa,
    v.estado_legal,
    v.estado_geoespacial,
    COALESCE(af.total_superficie_afectada_ha, 0) AS total_superficie_afectada_ha,
    COALESCE(al.superficie_liberada_ha, 0) AS superficie_liberada_ha,
    COALESCE(af.total_superficie_afectada_ha, 0) - COALESCE(al.superficie_liberada_ha, 0) AS superficie_pendiente_ha,
    CASE 
        WHEN COALESCE(af.total_superficie_afectada_ha, 0) = 0 THEN 0
        ELSE ROUND((COALESCE(al.superficie_liberada_ha, 0) / af.total_superficie_afectada_ha) * 100, 2)
    END AS porcentaje_avance_legal,
    CASE 
        WHEN COALESCE(af.total_superficie_afectada_ha, 0) = 0 THEN 0
        ELSE ROUND((COALESCE(af_geo.superficie_con_geometria, 0) / af.total_superficie_afectada_ha) * 100, 2)
    END AS porcentaje_avance_geoespacial,
    COALESCE(al.total_convenios_formalizados_ran, 0) AS total_convenios_formalizados_ran,
    COALESCE(al.total_convenios_colectivos_formalizados_ran, 0) AS total_convenios_colectivos_formalizados_ran,
    COALESCE(al.total_convenios_individuales_formalizados_ran, 0) AS total_convenios_individuales_formalizados_ran,
    COALESCE(al.total_colectivo_ha, 0) AS total_colectivo_ha,
    COALESCE(al.total_individual_ha, 0) AS total_individual_ha
FROM vw_tramo_nucleo_estado v
JOIN tramo t ON t.id_tramo = v.id_tramo AND t.activo = TRUE
JOIN frente f ON f.id_frente = v.id_frente AND f.activo = TRUE
JOIN nucleo_agrario n ON n.id_nucleo = v.id_nucleo AND n.activo = TRUE
JOIN municipio m ON m.id_municipio = n.id_municipio AND m.activo = TRUE
JOIN entidad_federativa ef ON ef.id_entidad = m.id_entidad AND ef.activo = TRUE
LEFT JOIN (
    SELECT id_tramo_nucleo, SUM(COALESCE(superficie_afectada_ha, 0)) AS total_superficie_afectada_ha
    FROM afectacion WHERE activo = TRUE GROUP BY id_tramo_nucleo
) af ON af.id_tramo_nucleo = v.id_tramo_nucleo
LEFT JOIN (
    SELECT id_tramo_nucleo, SUM(COALESCE(superficie_afectada_ha, 0)) AS superficie_con_geometria
    FROM afectacion WHERE activo = TRUE AND geometria_afectacion IS NOT NULL GROUP BY id_tramo_nucleo
) af_geo ON af_geo.id_tramo_nucleo = v.id_tramo_nucleo
LEFT JOIN AgrupacionLiberada al ON al.id_tramo_nucleo = v.id_tramo_nucleo;
```

#### Diseño objetivo de estados para el Corte 2

Las vistas nuevas o reconstruidas deberán partir de `Proyecto → Tramo →
Tramo_Núcleo → Afectación`, sin `Frente`, y separar estas dimensiones:

```text
estado_operativo   sensibilización, caminamiento, afectación y asamblea
estado_registral   borrador, firmado, ingresado_ran, inscrito_ran
estado_financiero  pendiente_fifonafe, listo_pago, pagado
estado_terminal    ordinario, fuera_seguimiento_expropiacion,
                   fuera_seguimiento_comunidad_indigena
estado_liberacion  pendiente, en_proceso, liberado, no_aplica_terminal
```

Una afectación ordinaria sólo será `liberada` cuando exista evidencia del pago
aplicable. La inscripción ante el RAN alimenta `estado_registral`, pero no
cierra `estado_liberacion`. El estado de Tramo_Núcleo será una agregación que
puede ser mixta y nunca deberá ocultar afectaciones terminales. El SQL exacto
se definirá en la propuesta de migración expansiva y no forma parte de este
ajuste documental.

## Reglas de Negocio Implementadas en Base de Datos

Esta sección documenta las reglas de negocio críticas que se implementan mediante CHECK constraints en PostgreSQL para garantizar integridad de datos desde la capa de persistencia. Estas reglas provienen directamente del proceso descrito en `Descripción proceso.md` (fuente de verdad).

### RN-1: Validación de Tipo de Convenio por Tipo de Afectación

**Ubicación**: Tabla `convenio`, constraint `chk_tipo_convenio_por_afectacion`

**Regla**: Los tipos de convenio permitidos dependen del tipo de afectación:
- **Derechos Colectivos**: 'cop_original', 'modificatorio', 'superficie_adicional', 'obras_complementarias'
- **Derechos Individuales**: 'cop_original', 'modificatorio', 'ampliacion', 'ampliacion_remanente'

**Fuente**: `Descripción proceso.md`, secciones “5.2 Variantes colectivas” y
“6.1 Variantes individuales”.
> Colectivos: COP original, modificatorio, superficie adicional y obras
> complementarias. Individuales: COP original, modificatorio, ampliación y
> ampliación remanente.

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

**Fuente**: `Descripción proceso.md`, sección “5.2 Variantes colectivas”.
> En obras complementarias no se captura `monto_bdt`. El pago corresponde
> solamente al valor pactado por la superficie.

**Implementación**:
```sql
CONSTRAINT chk_bdt_no_obras_complementarias CHECK (
    (tipo_convenio = 'obras_complementarias' AND monto_bdt IS NULL)
    OR
    (tipo_convenio != 'obras_complementarias')
)
```

**Justificación**: En el alcance funcional vigente, las obras complementarias
no capturan `monto_bdt`. Esta restricción previene registrar un componente
económico que no corresponde, sin modelar inventarios ni procesos de avalúo.

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

**Fuente**: `Descripción proceso.md`, sección “6.1 Variantes individuales”.
> El modificatorio individual ajusta fecha y montos; no registra nueva
> superficie ni BDT.

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
> "La distinción principal es jurídica. Superficie Total Real Afectada (Ha) mide el impacto sobre las tierras inalienables que son de uso comunal y requieren asambleas, mientras que Superficie Total (Ha.) se captura en expedientes individuales de propiedad social para medir la afectación de una parcela con titular específico."

**Contexto Jurídico Detallado**:

Los dos campos de superficie reflejan una diferencia fundamental en el derecho agrario mexicano:

1. **`superficie_total_ha` - Para Derechos INDIVIDUALES (Parcelas)**:
   - Mide la superficie específica de una **parcela con titular registrado**
   - El titular es una persona física identificada (ejidatario o comunero)
   - Se captura en **expedientes individuales de propiedad social** mediante negociación directa
   - **NO requiere asamblea** - la autorización la da el titular directamente
   - Proceso: Sensibilización → Caminamiento → Negociación directa con el titular → Firma
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
| Individual | Ampliación | `superficie_ampliacion_ha` |
| Individual | Ampliación Remanente | `superficie_ampliacion_ha` |
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
- El Modificatorio Individual (al ser un ajuste económico individual sin afectación adicional de superficie) NO requiere inscripción en el RAN, según lo define el proceso (Fase 3B). El diseño exige estrictamente que sus campos registrales queden nulos a través del constraint `chk_modificatorio_individual_restricciones`.

**4. Ubicación Normalizada de "No. de Parcela / Solar"**:
- El número de parcela/solar (cuando aplica a tierras colectivas) describe funcionalmente el "Destino de la Superficie" en la asamblea de Derechos Colectivos (Fase 3A). Se movió lógicamente hacia la tabla `afectacion` junto al campo `destino_superficie`, ya que pertenece puramente a los datos formales de la afectación y no al registro genérico del cruce `tramo_nucleo`.

**5. Trazabilidad Determinista del Quórum (id_padron)**:
- Se añadió explícitamente una llave foránea `id_padron` en la tabla `asamblea`. Aunque el sistema podría derivar el padrón cruzando la fecha de la asamblea con la fecha del padrón, esta llave foránea asegura inmutabilidad jurídica. Hace que cada acta de asamblea esté unida irrefutablemente a una versión histórica del censo de población para probar la legalidad del quórum.

**6. Excepciones Operativas — implementación parcial y diseño objetivo**:
- La base vigente contiene banderas en `nucleo_agrario` y `tramo_nucleo`, y
  triggers que bloquean sólo parte de las operaciones incompatibles. Esto no
  implementa todavía una salida terminal completa ni permite clasificar una
  sola afectación. El Corte 2 deberá representar, cuando sea necesario, la
  excepción en `afectacion`, bloquear todas las etapas ordinarias posteriores
  y conservar únicamente notas, documentos y auditoría. La marca “No afecta
  tierras de uso común” bloqueará sólo la ruta colectiva.

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
- **Estatus:** Esta desviación arquitectónica hacia la normalización (abandonar columnas `_2` del Excel original) ha sido formalmente **avalada y aprobada por los stakeholders**, convirtiéndose en la estrategia oficial del sistema.

**Alternativa Rechazada**: Campos duplicados con sufijo "_2" (e.g. `ingreso_ran_fecha_2`)
- Desventaja: Rompe la Primera Forma Normal.
- Desventaja: Traslada artificialmente las limitaciones bidimensionales de una hoja de cálculo al motor de base de datos.

---

#### Diferencia entre superficie_total_ha y superficie_real_afectada_ha

Según el stakeholder y el documento `Descripción proceso.md`, la distinción es **jurídica** y refleja diferencias fundamentales en el derecho agrario mexicano:

> "Superficie Total Real Afectada (Ha) mide el impacto sobre las tierras inalienables que son de uso comunal y requieren asambleas, mientras que Superficie Total (Ha.) se captura en expedientes individuales de propiedad social para medir la afectación de una parcela con titular específico."

**Regla Implementada**:
- **`superficie_total_ha`**: Se usa SOLO para afectaciones INDIVIDUALES
  - Mide la superficie de una **parcela con titular específico** (ejidatario o comunero identificado)
  - Se captura en **expedientes individuales de propiedad social** mediante negociación directa
  - **NO requiere asamblea** - la autorización la da el titular directamente
  - Proceso: Sensibilización → Caminamiento → Negociación directa con el titular → Firma
  
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

Las propiedades de esta sección son un inventario histórico y requieren
reescritura contra los requisitos vigentes antes de convertirse en pruebas.
Toda referencia a `Frente`, cascadas físicas o liberación por simple
inscripción RAN queda invalidada por el modelo actual.

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

### Property 3: Cardinalidad de Proyecto y Tramo

*Para cualquier* Proyecto, el sistema debe permitir uno o más Tramos activos,
y cada Tramo debe estar asociado exactamente a un Proyecto válido.

**Validates: Requirements 2.2, 2.4**

**Estrategia de Implementación:**
- Generar Proyectos con cantidades variables de Tramos
- Para cada Tramo, verificar que `id_proyecto` referencia un Proyecto existente
- Validar la baja lógica y la restricción de padres con hijos activos

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
- Generar pares aleatorios de Tramos y Núcleos Agrarios
- Si `ST_Intersects(tramo, nucleo)` es verdadero, verificar que `ST_Intersects(nucleo, tramo)` también es verdadero
- Validar que el área de intersección es consistente sin importar el orden

### Property 8: Validación de Requisitos de Convenio según Tipo

*Para cualquier* Convenio creado, los campos requeridos deben cumplir con las reglas de validación específicas del tipo: cop_original requiere fecha de anuencia y minuta de asamblea, modificatorio requiere referencia a cop_original previo, superficie_adicional requiere nueva superficie afectada.

**Validates: Requirements 5.1, 5.2, 5.3, 5.4**

**Estrategia de Implementación:**
- Generar Convenios aleatorios de cada tipo
- Para tipo cop_original: validar que `fechaAnuencia` y `minutaAsamblea` estén presentes
- Para tipo modificatorio: validar que `convenioAnteriorId` referencie un cop_original existente
- Intentar crear Convenio sin campos requeridos debe fallar

### Property 9: Progresión de Estados de Convenio

*Para cualquier* Convenio, la transición registral debe seguir el flujo
válido: Borrador → Firmado → Ingresado_RAN → Inscrito_RAN. No se permiten
transiciones hacia atrás ni saltos de estados.

**Validates: Requirements 5.5, 8.1**

**Estrategia de Implementación:**
- Generar Convenios en diferentes estados
- Intentar transicionar de Borrador a Inscrito_RAN directamente debe fallar
- Intentar transicionar de Inscrito_RAN a Firmado (regresión) debe fallar
- Validar que sólo se acepten las transiciones consecutivas

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

*Para cualquier* Núcleo Agrario, Tramo-Núcleo o Afectación, el sistema debe
registrar y hacer cumplir Expropiación Directa, Comunidad Indígena y No Afecta
Tierras de Uso Común en su alcance correcto.

**Validates: Requirements 19.1, 19.2, 19.3, 19.4**

**Estrategia de Implementación:**
- Crear casos terminales completos y parciales
- Verificar que se bloqueen todas las actuaciones ordinarias posteriores
- Verificar que notas, documentos y auditoría sigan permitidos
- Verificar que “No afecta tierras de uso común” no bloquee la ruta individual
- Verificar reportes mixtos sin contar terminales como liberados o pendientes

### Property 14: Trazabilidad de Oficios FIFONAFE

*Para cualquier* proceso de indemnización, el sistema debe garantizar la captura exacta de la cadena interinstitucional de oficios de FIFONAFE con sus fechas y números respectivos.

**Validates: Requirements 9.3, 9.4**

**Estrategia de Implementación:**
- Generar un flujo de indemnización registrando los 4 oficios obligatorios (FIFONAFE, DGAOPR, Representación)
- Verificar que la vista de seguimiento muestre el estado de completitud basado en la integridad de la cadena documental

## Despliegue e Infraestructura

Esta sección detalla la arquitectura de despliegue, configuración de infraestructura, estrategias de alta disponibilidad y respaldos para cumplir con los requerimientos no funcionales RNF-13 (disponibilidad 99%) y RNF-14 (respaldos automáticos diarios).

### Arquitectura de Despliegue (Servidor Único)

Dado el hardware disponible, el sistema se despliega en una arquitectura de servidor único (Monolítica) optimizada para aprovechar los recursos locales. Se recomienda el uso de contenedores (ej. Docker Compose) para facilitar el encapsulamiento y orquestación de los servicios dentro del mismo nodo.

```
┌─────────────────────────────────────────────────────────┐
│               Servidor Único (Ubuntu 24.04)             │
│   (4 vCPU, 8 GB RAM, 100 GB SSD)                        │
│                                                         │
│   ┌─────────────────────────────────────────────────┐   │
│   │ Reverse Proxy (Nginx)                           │   │
│   │ - Terminación SSL/TLS                           │   │
│   │ - Enrutamiento a frontend y API                 │   │
│   └────────────────────────┬────────────────────────┘   │
│                            ↓                            │
│   ┌────────────────────────┴────────────────────────┐   │
│   │ Contenedor App (Node.js/Python)                 │   │
│   │ - API REST                                      │   │
│   │ - Servicios GIS                                 │   │
│   └────────────────────────┬────────────────────────┘   │
│                            ↓                            │
│   ┌────────────────────────┴────────────────────────┐   │
│   │ Contenedor Base de Datos                        │   │
│   │ - PostgreSQL + PostGIS                          │   │
│   └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Componentes de Infraestructura

**1. Servidor Físico / Virtual**
- **Sistema Operativo**: Ubuntu 24.04.3 LTS (Kernel Linux 6.8)
- **Arquitectura**: x86_64
- **CPU**: 4 vCPU
- **Memoria RAM**: 8 GB (7.6 GiB efectivos)
- **Almacenamiento**: 100 GB SSD (aprox. 86 GB disponibles)

**2. Proxy Inverso y Servidor Web**
- **Tecnología**: Nginx
- **Funcionalidades**: 
  - Gestión de certificados SSL (Let's Encrypt)
  - Servir archivos estáticos del frontend
  - Redirección de tráfico `/api` al backend

**3. Servidor de Aplicación**
- **Runtime**: Node.js 18+ o Python 3.10+
- **Configuración**: Un único proceso o cluster limitado a 2-3 workers para no saturar los 4 vCPU del servidor, balanceando los requerimientos de la BD.
- **Validación RNF-1**: Obligatorio realizar pruebas de carga empíricas (ej. k6) para confirmar que esta arquitectura mononodo soporta 50 usuarios concurrentes sin degradación.

**4. Base de Datos**
- **Versión**: PostgreSQL 14+ con PostGIS 3.3+
- **Configuración Optimizada para 8GB RAM**:
  - `shared_buffers` = 2GB (25% de RAM)
  - `work_mem` = 16MB
  - `maintenance_work_mem` = 512MB
  - `effective_cache_size` = 4GB

### Estrategia de Disponibilidad y Recuperación (RNF-13)

Al contar con un servidor único, la disponibilidad del 99% se enfoca en resiliencia del software más que en redundancia de hardware.
- **Auto-recuperación**: Uso de Docker (restart policies) o Systemd para reiniciar automáticamente los servicios si fallan.
- **Monitoreo Local**: Scripts ligeros o herramientas como `htop` y `pm2/docker stats` para vigilar el consumo de CPU y disco (evitando saturar los 86 GB disponibles).
- **Mantenimiento**: Implicará ventanas de downtime planificadas para actualizaciones (despliegue blue/green no es factible por limitaciones de RAM).

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
  # Copia obligatoria a almacenamiento offsite (S3) para prevenir pérdida por falla de disco
  aws s3 sync $BACKUP_DIR s3://backups-liberacion-derechos/postgresql/
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
-- C-03: Función corregida para cálculo de superficie liberada por tramo_nucleo.
-- La versión anterior usaba una suma directa de superficie_afectada_ha que
-- ignoraba la lógica de modificatorios vigentes (ROW_NUMBER por convenio padre).
-- Esta versión delega a fn_calcular_superficie_liberada_afectacion(), garantizando
-- que ambas rutas de cálculo usen exactamente la misma lógica de negocio.
CREATE OR REPLACE FUNCTION calcular_superficie_liberada(p_id_tramo_nucleo INTEGER)
RETURNS NUMERIC AS $$
DECLARE
    v_total NUMERIC := 0;
BEGIN
    SELECT COALESCE(
        SUM(fn_calcular_superficie_liberada_afectacion(a.id_afectacion)),
        0
    )
    INTO v_total
    FROM afectacion a
    WHERE a.id_tramo_nucleo = p_id_tramo_nucleo
      AND a.activo = TRUE;

    RETURN v_total;

EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION
            'Error en calcular_superficie_liberada(tramo_nucleo=%): % (SQLSTATE: %)',
            p_id_tramo_nucleo, SQLERRM, SQLSTATE;
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

> **Referencia histórica.** Los ejemplos de esta sección no corresponden a la
> suite Python/React vigente y algunos todavía usan `Frente`. Para el Corte 2
> deberán sustituirse por pruebas reales de API, servicios, PostgreSQL y
> frontend basadas en `Proyecto → Tramo → Tramo_Núcleo → Afectación`, la
> secuencia obligatoria, las salidas terminales y el cierre después del pago.

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
          role: fc.constant('visualizador')
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
    fc.constant('cop_original'),
    fc.constant('modificatorio'),
    fc.constant('superficie_adicional'),
    fc.constant('obras_complementarias'),
    fc.constant('ampliacion'),
    fc.constant('ampliacion_remanente')
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
describe('E2E: Creación de Convenio cop_original', () => {
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
  
  it('debe permitir crear convenio cop_original con todos los campos requeridos', async () => {
    // Navegar a formulario de convenio
    await page.click('text=Convenios')
    await page.click('text=Nuevo Convenio')
    
    // Seleccionar tipo
    await page.selectOption('[name="tipo"]', 'cop_original')
    
    // Llenar campos requeridos para cop_original
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
    await page.selectOption('[name="tipo"]', 'cop_original')
    
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
