# Modelo Funcional Objetivo — SOFTWARE-PA

> **Autoridad:** Documento canónico de alcance y especificación funcional del sistema SOFTWARE-PA.  
> **Precedencia:** Define las reglas de negocio, los hechos administrativos y los límites del dominio a los que deben subordinarse la arquitectura técnica, el diccionario de datos y las interfaces de usuario y programación.

---

## 1. Propósito

**SOFTWARE-PA** es un sistema informático diseñado para digitalizar, ordenar y estructurar el seguimiento administrativo y operativo que la Procuraduría Agraria (PA) realiza respecto a la liberación de derecho de vía en proyectos estratégicos (principalmente ferroviarios) que atraviesan tierras sujetas al régimen de propiedad social.

El propósito central es **sustituir las hojas de cálculo Excel operativas** por una plataforma multiusuario estructurada, consistente y trazable, capaz de:

1. Registrar con precisión los hechos administrativos, documentales y financieros de cada núcleo agrario y parcela afectada.
2. Mantener la trazabilidad del estado procesal sin pérdida de datos ni dependencias de memoria informal.
3. Generar de forma determinista y deduplicada los indicadores clave de desempeño (KPI), resúmenes de avance periódico y tableros ejecutivos requeridos por la dirección del proyecto.
4. Proveer un visor cartográfico de apoyo territorial que asocie la información administrativa con el trazo y los perímetros agrarios.

El sistema está diseñado para la operación práctica de las residencias y brigadas en campo y oficinas centrales, garantizando la integridad de los datos a lo largo de todo el ciclo de liberación.

---

## 2. Alcance

### 2.1 Dominio cubierto

El sistema abarca exclusivamente la **propiedad social** en México:
- **Ejidos** y **Comunidades agrarias** legalmente constituidos o reconocidos.
- **Tierras de uso común** (derechos colectivos del núcleo agrario).
- **Parcelas individuales** (derechos individuales de ejidatarios, comuneros o posesionarios reconocidos).
- **Zonas y destinos específicos** dentro del régimen social: parcelas escolares, unidades agrícolas industriales para la mujer (UAIM), solares en asentamientos humanos cuando forman parte del expediente agrario, canales, caminos y zonas de infraestructura.

### 2.2 Límites y exclusiones explícitas

Quedan expresamente **fuera del alcance funcional**:
- **Propiedad privada:** No gestiona predios particulares ni régimen de pequeña propiedad civil.
- **Catastro urbano y Registro Público de la Propiedad (RPP):** No sustituye registros inmobiliarios civiles estatales ni municipales.
- **Modelado procesal judicial o litigioso:** No es un gestor de juicio agrario ni sustituye los expedientes de los Tribunales Unitarios Agrarios (TUA).
- **Procedimiento formal de expropiación:** El sistema no tramita ni modela el expediente expropiatorio formal sustanciado ante SEDATU o INDAABIN. La expropiación se registra únicamente como condición o evento operativo de seguimiento.
- **Gestión financiera bancaria / tesorería:** Registra las indemnizaciones autorizadas y la evidencia de los pagos efectuados, pero no procesa dispersiones bancarias directas ni emisión de cheques.

---

## 3. Principio Operativo Excel-First y Precedencia Documental

### 3.1 Regla invariable del proyecto

> **SOFTWARE-PA debe demostrar correspondencia estricta con el modelo operativo de los archivos Excel, NO una modelación exhaustiva del Derecho Agrario mexicano.**

El objetivo del software es resolver la necesidad operativa real plasmada en las herramientas de seguimiento en uso. Toda funcionalidad, entidad, pantalla o flujo debe responder a:
1. **Evidencia directa en los libros Excel operativos** (columnas, hojas, celdas, fórmulas, notas de campo o prácticas de captura observadas), o
2. **Una decisión funcional expresamente aprobada y justificada** por el equipo del proyecto.

### 3.2 Rol de la normativa agraria y documentos interpretativos

La legislación agraria (Artículo 27 Constitucional, Ley Agraria y su Reglamento en Materia de Ordenamiento de la Propiedad Rural), los lineamientos institucionales de la Procuraduría Agraria (en materia de Convenios de Ocupación Previa y Expropiación), los manuales del Registro Agrario Nacional (RAN), del FIFONAFE, INDAABIN e INPI, así como los flujogramas de procesos:

- **Son fuentes de interpretación y contexto:** Permiten comprender la semántica, el propósito y las dependencias de los actos administrativos (p. ej. qué es una primera o segunda convocatoria, qué implica la inscripción registral o para qué sirve el oficio de no conflictos).
- **NO son generadores automáticos de alcance:** Ninguna norma, reglamento o diagrama autoriza por sí mismo la creación de tablas, módulos, etapas obligatorias, máquinas de estados o validaciones si no existe necesidad real de captura o reporting comprobada en los Excel.

### 3.3 Jerarquía de precedencia documental

En caso de duda o aparente contradicción entre artefactos, rige la siguiente precedencia:

1. **Archivos Excel operativos + MODELO_FUNCIONAL.md:** Autoridad canónica superior respecto al alcance, hechos a modelar y reglas del negocio.
2. **FUENTES_Y_COBERTURA_EXCEL.md:** Prueba de correspondencia y matriz de trazabilidad entre cada dato de fuente y el sistema.
3. **Código backend ejecutable + migraciones de base de datos:** Realidad técnica implementada y verificable.
4. **ARQUITECTURA.md y DICCIONARIO_DATOS.md:** Documentación técnica de cómo está construido el sistema y cómo se representan sus datos.
5. **API.md y openapi.json:** Contrato formal de integración y consumo de servicios.
6. **Fuentes interpretativas (leyes, reglamentos, flujogramas):** Marco contextual conceptual.

---

## 4. Estructura y Jerarquía del Modelo Funcional

El modelo de SOFTWARE-PA se estructura a partir de la relación entre proyectos estratégicos y núcleos agrarios, bifurcándose en las rutas de derechos colectivos y derechos individuales.

```text
Proyecto
└── ProyectoNucleo
    └── Núcleo Agrario
        ├── Datos generales y tenencia
        ├── Órgano de Representación y Vigilancia (ORV)
        ├── Padrón ejidal / comunal
        ├── Sensibilización
        ├── Caminamiento
        │
        ├── Derechos colectivos (Tierras de uso común / superficies del núcleo)
        │   ├── Asamblea
        │   │   ├── Convocatorias (1ª, 2ª, ulterior)
        │   │   └── Trámite RAN del acta de asamblea
        │   ├── Afectación colectiva
        │   │   ├── Destino(s) de superficie y hectáreas administrativas
        │   │   ├── Avalúo simple (monto INDAABIN)
        │   │   ├── Convenio(s) de Ocupación Previa (COP / Modificatorio / Adicional / Obras)
        │   │   │   └── Trámite RAN del convenio
        │   │   ├── Trámite FIFONAFE / No conflictos (compartible entre afectaciones)
        │   │   └── Indemnización por afectación
        │   │       └── Pago(s)
        │   └── Retiro de fondos (Asamblea de retiro + Trámite RAN de retiro)
        │
        └── Derechos individuales
            └── Parcela (Identificada por único no_parcela canónico)
                ├── Titular(es), constancias, certificados y folios de derechos
                └── Afectación individual
                    ├── Superficie administrativa y destino
                    ├── Avalúo simple (monto INDAABIN)
                    ├── Convenio(s) de Ocupación Previa (COP / Modificatorio / Ampliación / Remanente)
                    │   └── Trámite RAN del convenio
                    ├── Trámite FIFONAFE / No conflictos (compartible entre parcelas)
                    └── Indemnización por afectación
                        └── Pago(s)
```

### 4.1 Principios rectores de la estructura

- **ProyectoNucleo como eje operativo:** El cruce entre un Proyecto y un Núcleo Agrario constituye la unidad fundamental de gestión administrativa y asignación de responsabilidades.
- **Desacoplamiento de Tramo:** Históricamente se consideró el "Tramo" como jerarquía estructural estricta. En el modelo vigente, **Tramo NO es una entidad jerárquica obligatoria**. Las referencias a tramo (`CLAVE DEL TRAMO`, `NÚMERO DE TRAMO`, `CONSECUTIVO`) se capturan como referencias administrativas repetibles asociadas a `ProyectoNucleo`, sin condicionar la navegación ni restringir permisos.
- **Eliminación de conceptos históricos obsoletos:** `TramoNucleo` como expediente maestro obligatorio y `AfectacionCiclo` no forman parte del modelo funcional. La trazabilidad temporal se preserva mediante los instrumentos jurídicos y los eventos fechados.
- **Autorización por proyecto:** La asignación de permisos a operadores y analistas se realiza a nivel Proyecto (`UsuarioProyecto`), garantizando un aislamiento estricto y seguro.

---

## 5. Bifurcación Funcional: Colectivo vs Individual

El sistema reconoce y trata de forma independiente las dos rutas operativas de liberación agraria:

### 5.1 Ruta Colectiva (Uso Común y Tierras del Núcleo)

Aplica sobre superficies que pertenecen a la colectividad del ejido o comunidad.
- **Entidad de inicio:** Se genera una `Afectacion` de tipo colectivo asociada directamente al `ProyectoNucleo`, **sin requerir la existencia de una Parcela**.
- **Actividades previas:** Sensibilización y caminamientos comunitarios.
- **Asamblea General:** Exclusiva de la ruta colectiva. Es el órgano supremo que otorga la anuencia y autoriza la suscripción de convenios.
  - Se registran convocatorias (primera, segunda o ulterior) con fecha de expedición, fecha programada y resultado.
  - La asamblea se considera realizada únicamente cuando alguna convocatoria tiene resultado `celebrada`.
  - La asamblea puede autorizar uno o múltiples convenios colectivos.
- **RAN del Acta:** Trámite registral específico para inscribir el acta de asamblea de anuencia ante el Registro Agrario Nacional.
- **Convenios Colectivos:** Instrumentos suscritos con el Comisariado Ejidal o de Bienes Comunales.
  - Tipos válidos: `cop_original`, `modificatorio`, `superficie_adicional`, `obras_complementarias`.
- **RAN del Convenio:** Trámite registral específico para el convenio colectivo, independiente del trámite del acta.
- **Retiro de fondos:** Proceso especial que requiere asamblea específica de retiro de fondos y su consecuente inscripción en RAN.
- **FIFONAFE Colectivo:** Trámite institucional que resguarda los fondos depositados por la entidad promovente; requiere la comprobación de una cadena estricta de cuatro oficios y el análisis de no conflictos.
- **Indemnización y Pago Colectivo:** Asignación de montos resueltos y registro de pagos efectivos a favor del núcleo.

### 5.2 Ruta Individual (Parcelas Tituladas o Posesiones)

Aplica sobre porciones parceladas con derechos delimitados a favor de ejidatarios, comuneros o posesionarios.
- **Entidad central:** La `Parcela`, identificada unívocamente por su `no_parcela`.
- **Titularidad:** Uno o varios titulares asociados a la parcela con acreditación documental (certificado parcelario, folio de derechos, constancia de vigencia).
- **Regla del sistema:** **Asamblea NO es requisito ni estructura de captura de la ruta individual**, ya que no forma parte del seguimiento parcelario en los Excel operativos.
- **Convenios Individuales:** Se asocian directamente a la afectación de la parcela.
  - Tipos válidos: `cop_original`, `modificatorio`, `ampliacion`, `ampliacion_remanente`.
- **RAN del Convenio Individual:** Inscripción registral del instrumento individual ante el RAN.
- **FIFONAFE Individual:** Cuando aplique, se gestiona para acreditar titularidad y liberación de fondos individuales; un mismo trámite FIFONAFE puede amparar afectaciones de múltiples parcelas del mismo núcleo.
- **Indemnización y Pago Individual:** Liquidación económica realizada directamente al titular o apoderado legal acreditado.

---

## 6. Manejo de Parcela y Número de Parcela

### 6.1 Identificador Funcional Canónico Único

En las fuentes Excel coexisten frecuentemente dos columnas con denominaciones similares:
- `NO. PARCELA` / `NO PARCELA/SOLAR`
- `NO. PARCELA PPT`

La auditoría exhaustiva de los datos confirmó que ambas columnas refieren **al mismo identificador funcional de la parcela** según el padrón o el plano del núcleo agrario.

**Regla obligatoria de modelado:**
1. Existe un **único identificador funcional canónico**: `Parcela.no_parcela`.
2. No debe inventarse un segundo campo de dominio independiente (`no_parcela_ppt`) ni un dominio parcelario paralelo.
3. Tratamiento de trazabilidad:
   - Si `NO. PARCELA` y `NO. PARCELA PPT` coinciden o sólo uno de ellos tiene valor: se almacena en `no_parcela` y la fuente auxiliar queda como `REFERENCIA`.
   - Si ambos presentan valores divergentes y contradictorios: se conserva el valor primario, se registra la discrepancia en trazabilidad y se marca como `REVISAR` para aclaración en campo.
4. Estados de titularidad especiales en Excel (`EN TRÁMITE`, `EN INVESTIGACIÓN`, `SIN ASIGNAR`, `EN CONFLICTO`): Se registran como metadatos de seguimiento o estado del requisito, **sin inventar personas físicas ficticias**.

---

## 7. Convenios y Dimensiones Operativas

### 7.1 Naturaleza repetible

Los convenios de ocupación previa son instrumentos jurídicos repetibles en el tiempo. Cada convenio constituye una fila/registro independiente con sus propias fechas (firma programada, firma real), montos convenidos, superficie amparada y seguimiento registral.

### 7.2 Tipología de convenios según ámbito

| Ámbito | Tipo de Convenio (`tipo_convenio`) | Significado Operativo |
|---|---|---|
| **Colectivo** | `cop_original` | Convenio inicial de ocupación sobre uso común. |
| **Colectivo** | `modificatorio` | Instrumento que ajusta cláusulas o especificaciones sin agregar superficie sustancial. |
| **Colectivo** | `superficie_adicional` | Convenio que incorpora nueva superficie de uso común al proyecto. |
| **Colectivo** | `obras_complementarias` | Convenio enfocado en mitigaciones, pasos o infraestructura pactada. |
| **Individual** | `cop_original` | Convenio inicial firmado con el titular de la parcela. |
| **Individual** | `modificatorio` | Modificación a las condiciones del convenio parcelario inicial. |
| **Individual** | `ampliacion` | Incremento de superficie afectada en la misma parcela. |
| **Individual** | `ampliacion_remanente` | Afectación de fracciones remanentes no útiles para el titular. |

### 7.3 Modalidades especiales: La Permuta

En la práctica observada existen casos excepcionales de **permuta** de tierras. La permuta:
- **NO constituye un tipo ordinario de convenio** en el catálogo base.
- Se registra como un `tipo_convenio = 'cop_original'` con el atributo `modalidad_especial = 'permuta'`, complementado con descripción detallada y soporte documental.
- Si en revisiones jurídicas posteriores se presenta un instrumento formal no asimilable a COP, se clasifica como `tipo_instrumento = 'otro'`.

### 7.4 Dimensión del Ciclo Operativo COP

Independientemente del tipo de instrumento, el sistema clasifica las gestiones en el catálogo `tipo_cop_operativo`:
- `ORIGEN`
- `ADICIONAL`
- `2A_ADICIONAL` (mantenido conforme a catálogo implementado; ver sección de decisiones pendientes)
- `COMPLEMENTARIAS`
- `TRANSVERSALES`

Esta clasificación permite al dashboard y a los reportes agrupar los avances conforme a los ciclos de financiamiento y metas operativas institucionales.

### 7.5 Relaciones Multidestino y No Aditividad de Montos

Un convenio colectivo puede amparar afectaciones con múltiples destinos de suelo (p. ej. uso común, canal y camino). En estos casos:
- Se vincula el convenio con sus respectivas afectaciones mediante `ConvenioAfectacion`.
- La superficie física por destino se reporta según la afectación específica (`AfectacionUnidadAgraria.superficie_afectada_ha`).
- El monto pactado (`c.monto_100`) pertenece al convenio en su totalidad. **El monto es estrictamente NO ADITIVO entre filas de desglose por destino**; no se prorratea artificialmente y debe computarse una sola vez por instrumento en los balances financieros oficiales.

---

## 8. Tramitaciones ante el Registro Agrario Nacional (RAN)

El sistema modela con precisión la interacción con el registrador agrario nacional bajo las siguientes reglas:

### 8.1 Separación entre Acta y Convenio

El seguimiento registral no es un atributo de texto plano dentro de la asamblea o el convenio. Se gestiona mediante la entidad `TramiteRan` y su historial de `TramiteRanEvento`:
- **RAN del Acta:** Ampara exclusivamente la inscripción del acta de asamblea de anuencia (`id_asamblea`).
- **RAN del Convenio:** Ampara exclusivamente la inscripción del convenio celebrado (`id_convenio`).
- **RAN de Órgano de Representación:** Ampara la inscripción del acta de elección de comisariados (`id_orv`).

### 8.2 Secuencia de eventos y distinción de hitos

Un trámite registral atraviesa diversos eventos fechados: `ingreso`, `prevencion`, `subsanacion`, `calificacion`, `inscripcion`, `reingreso`.

Reglas funcionales para reporting:
1. **Ingreso:** Se reconoce por el evento de tipo `ingreso` (o el primer `reingreso`). Múltiples reingresos sobre el mismo expediente se consideran incidencias del mismo trámite y no duplican el conteo de trámites iniciados.
2. **Calificación:** La emisión de una calificación registral (favorable o con observaciones) es una actuación intermedia; **NO equivale a inscripción**.
3. **Inscripción definitiva:** Constituye el hito de éxito del trámite. Se deriva exclusivamente del evento con tipo `inscripcion` y su respectiva `fecha_evento`. Ninguna fecha de captura técnica ni fecha de calificación puede sustituir a la fecha de inscripción formal.

---

## 9. Procedimiento FIFONAFE e Informe de No Conflictos

El Fideicomiso Fondo Nacional de Fomento Ejidal (FIFONAFE) interviene como custodio de los recursos indemnizatorios de la propiedad social.

### 9.1 Modelo funcional de FIFONAFE

- **Pertenencia:** El trámite (`TramiteFifonafe`) se asocia a `ProyectoNucleo`, diferenciando su `ambito` (`colectivo` o `individual`).
- **Cobertura múltiple:** Un solo trámite FIFONAFE puede dar cobertura a múltiples afectaciones del mismo núcleo (`TramiteFifonafeAfectacion`). Esto refleja la práctica operativa donde un solo oficio de consulta ampara diversas parcelas o polígonos sin multiplicar trámites innecesariamente.

### 9.2 Cadena Colectiva de Cuatro Oficios

Para el ámbito colectivo, el seguimiento de la consulta de no conflictos requiere la verificación cronológica de cuatro oficios formales:
1. Oficio de solicitud / consulta de FIFONAFE a DGAOPR o Representación Estatal.
2. Oficio de turno interno de DGAOPR a Representación Estatal.
3. Oficio de informe / respuesta de la Representación Estatal a DGAOPR.
4. Oficio de respuesta y desahogo de DGAOPR o Representación ante el FIFONAFE.

**Hito de culminación:** El trámite colectivo se reporta como "completo" únicamente cuando los cuatro oficios cuentan con registro y fecha documental. Su fecha realizada corresponde a `MAX(fecha_oficio)`.

### 9.3 Independencia del Informe de No Conflictos

- El atributo `hay_conflictos` (triestado: Sí, No, Pendiente) y el informe de no conflictos constituyen un resultado de evaluación jurídica y social.
- **La emisión del informe de no conflictos es un hito independiente** de la completitud de la correspondencia de los cuatro oficios. No debe asumirse equivalencia automática entre ambos hechos.
- FIFONAFE **NO es el contenedor padre obligatorio de la indemnización ni del pago**.

---

## 10. Cadena Financiera: Indemnizaciones y Pagos

El flujo económico de liberación se rige por la cadena canónica:

```text
Pago → Indemnizacion → Afectacion → ProyectoNucleo → Proyecto
```

### 10.1 Indemnización

- La entidad `Indemnizacion` representa el acto administrativo mediante el cual se formaliza y autoriza el monto compensatorio derivado de una afectación.
- Está vinculada directamente a la `Afectacion` (máximo una indemnización activa por afectación).
- Conserva el avalúo institucional de referencia (monto INDAABIN simple), el monto total resuelto y la fecha de entrega del expediente por parte de SICT a la Procuraduría Agraria (`fecha_entrega_expediente_pa`).
- **Fecha de realización:** En los reportes de avance, el hito de indemnización resuelta se acredita exclusivamente mediante `fecha_resolucion`. Un estatus `pagado` sin fecha de resolución no se proyecta a periodos temporales.

### 10.2 Pagos Reales

- La entidad `Pago` representa cada desembolso económico efectivamente materializado a favor de los titulares o del núcleo agrario.
- Campos obligatorios: `fecha_pago`, `monto`, `beneficiario_nombre`, referencia documental del pago y observaciones.
- **Diferenciación estricta:**
  - Un Pago es un hecho financiero concreto (`indicador = 'pagos'`).
  - No debe confundirse con el estatus administrativo de la indemnización (`estatus = 'pagado'`).
  - No debe confundirse con el monto declarado en los convenios (`monto_100`), que es un compromiso pactado y no aditivo.
  - No debe confundirse con los retiros de fondos fiduciarios de FIFONAFE.
- Cada pago se agrega de forma independiente en reporting para evitar multiplicaciones por cruces N:M con afectaciones o destinos de suelo.

---

## 11. Eventos Especiales y Excepciones de Seguimiento

El sistema incluye el módulo de historia funcional `SeguimientoEvento`, diseñado para registrar contingencias, decisiones de campo e hitos no programados sin alterar destructivamente los registros principales.

### 11.1 Comunidad Indígena

- Se registra como atributo territorial del núcleo agrario (`comunidad_indigena = true`) y, en su caso, mediante eventos de consulta o seguimiento específico.
- **Regla estricta:** La presencia de población o régimen comunal indígena **NO genera una salida terminal automática del sistema**, ni marca al núcleo como "cancelado" o "fuera de alcance".
- La evidencia en los Excel demuestra casos reales de comunidades indígenas que continúan el procedimiento ordinario con suscripción de convenios COP y trámites registrales RAN.

### 11.2 Expropiación Directa

- Se registra como un evento de seguimiento (`motivo = 'expropiacion_directa'`) o como condición operativa de una afectación.
- Señala que la vía concertada (convenio de ocupación previa) no prosperó y que la promovente gestiona el decreto expropiatorio.
- **Regla estricta:** El registro de esta condición detiene la expectativa de firma de convenios ordinarios en dicha superficie, pero **NO da lugar a la construcción de un módulo procesal de litigio o decreto expropiatorio**.

### 11.3 No Afecta Tierras de Uso Común (No Afecta TUC)

- `afecta_tuc = false` significa únicamente que **no existe afectación a Tierras de Uso Común** conforme al seguimiento registrado.
- **Regla estricta:** La condición `afecta_tuc = false` **NO implica automáticamente**:
  1. Ausencia de cualquier afectación colectiva (pueden existir otros destinos colectivos observados en los Excel, tales como caminos, canales, asentamiento humano, solares o infraestructura).
  2. Cierre o salida del núcleo del sistema.
  3. Inexistencia de otros convenios o actuaciones colectivas aplicables.
  4. Bloqueo o suspensión de afectaciones y derechos individuales.
- **Semántica triestado:** `afecta_tuc = false` sólo se computa como certeza operativa cuando `tuc_revision_pendiente = false`. Un valor `NULL` representa estado por determinar y nunca equivale a falso ni a cero.

### 11.4 Suspensión, Reapertura, Cambio de Alcance y No Afectación

- Se modelan como eventos fechados con su respectivo soporte documental.
- Permiten pausar el seguimiento de un núcleo o parcela (por amparos, asambleas conflictivas o replanteamientos técnicos) y reactivarlo posteriormente cuando las condiciones lo permitan.
- No se infieren consecuencias jurídicas automáticas; el estado vigente del expediente se deriva deterministamente del último evento registrado (`vw_seguimiento_estado_actual`).

---

## 12. Reporting y Análisis de Datos

El reporting es una de las funciones cardinales de SOFTWARE-PA, modelado para reproducir fielmente la información gerencial de los Excel de seguimiento general.

### 12.1 Arquitectura en Dos Capas

Para garantizar que los agregados sean matemáticamente exactos y no se inflen por relaciones uno a muchos (1:N) o muchos a muchos (N:M):

1. **Capa 1 — Hitos Canónicos (`vw_hito_seguimiento`):**  
   Consolida cada hito operativo, jurídico o financiero en una unidad indivisible con clave única (`clave_hito`). Asigna sus fechas de negocio (programada y realizada), su ámbito, tipo de COP, tipo de convenio, destino y montos.
2. **Capa 2 — Proyección y Agregación:**  
   - **Avance Periódico (`vw_reporte_avance_periodo`):** Desglose estructurado en 15 columnas con filtros dimensionales (proyecto, entidad, ámbito, tipo COP, convenio, destino, año, mes, trimestre).
   - **Dashboard Ejecutivo (`vw_dashboard_kpi`):** Agregación anual por proyecto, indicador y año, deduplicada en origen.

### 12.2 Reporte de Estado Actual (Snapshot)

- `vw_reporte_snapshot_actual` refleja la situación presente acumulada (núcleos, parcelas intervenidas, superficies en hectáreas, condición TUC, comunidad indígena, metas COP).
- **Regla estricta:** No admite dimensión temporal (año, mes, trimestre) porque los atributos estructurales que no tienen fecha de negocio no deben falsificarse asignándoles fechas de creación técnica (`creado_en`).

### 12.3 Exclusión de Proyectos Inactivos

Todos los read-models de reporting excluyen de forma estricta aquellos proyectos cuyo atributo `activo` no sea verdadero (`activo IS NOT TRUE`), garantizando que los entornos de prueba, históricos o dados de baja no alteren los indicadores institucionales oficiales.

---

## 13. Principios y Uso del Componente Geoespacial

SOFTWARE-PA utiliza PostgreSQL con la extensión espacial PostGIS para brindar capacidades cartográficas bajo directrices de diseño sumamente claras:

1. **La geometría es apoyo cartográfico, NO un gate funcional:**  
   El mapa sirve para ubicar visualmente el trazo ferroviario, los polígonos ejidales y las parcelas, así como para navegar territorialmente.
2. **Independencia administrativa:**  
   Una afectación administrativa, un convenio o un pago pueden crearse y gestionarse plenamente **sin que exista todavía una geometría capturada** de la parcela o del área afectada. La falta de shapefile o coordenadas UTM no paraliza el seguimiento.
3. **No validación por intersección espacial obligatoria (`ST_Intersects`):**  
   No se requiere que el polígono de una parcela corte geométricamente la línea del trazo para permitir el alta del expediente, reconociendo discrepancias cartográficas históricas entre el plano de proyecto y el parcelamiento del RAN.
4. **Superficie administrativa capturada vs área calculada (`ST_Area`):**  
   El cálculo computacional del área mediante funciones espaciales (`ST_Area`) tiene carácter meramente indicativo y de apoyo cartográfico. Los cómputos, convenios, afectaciones, avalúos y pagos se rigen estrictamente por la **superficie administrativa capturada** (`superficie_afectada_ha` en afectaciones y unidades agrarias, o `superficie_ha` en convenios) proveniente de los documentos, convenios y actas de campo.

---

## 14. Requisitos Negativos Explícitos

Para mantener la integridad conceptual del sistema, se prohibe expresamente:

1. **NO restaurar Tramo como jerarquía obligatoria:** El flujo de navegación y autorización no debe forzarse a la cadena `Proyecto -> Tramo -> TramoNucleo`.
2. **NO reinstaurar `TramoNucleo` como expediente maestro:** El expediente reside en la relación `ProyectoNucleo`.
3. **NO reincorporar `AfectacionCiclo` al modelo funcional:** La temporalidad y los ciclos se gestionan mediante instrumentos tipificados y clasificaciones de COP.
4. **NO autorizar mediante `usuario_tramo`:** El mecanismo de control de acceso es estrictamente por proyecto (`usuario_proyecto`).
5. **NO imponer asamblea obligatoria en la ruta individual:** En el modelo de SOFTWARE-PA, la ruta individual se estructura por parcela y sus titulares. Asamblea y convocatoria no forman parte de los requisitos estructurales de captura y seguimiento de esta ruta, conforme a los Excel individuales auditados.
6. **NO tratar comunidad indígena como cancelación o salida del sistema:** Sigue siendo objeto de atención y seguimiento.
7. **NO modelar módulos jurídicos completos sin evidencia Excel:** Quedan prohibidos módulos aislados de juicios agrarios, expropiaciones solemnes o avalúos catastrales independientes.
8. **NO crear duplicidad de identificadores parcelarios:** Parcela sólo admite `no_parcela`.
9. **NO persistir campos auxiliares redundantes:** No se almacenan marcas "X", columnas de meses o trimestres fijos, ni conversiones directas a metros cuadrados que deban derivarse dinámicamente.

---

## 15. Decisiones Funcionales Pendientes

Existen definiciones operativas identificadas durante las auditorías de los archivos Excel que requieren un acuerdo formal de la dirección funcional del proyecto antes de sufrir cualquier alteración:

### 15.1 Caso `2A_ADICIONAL`

- **Situación:** En los libros de seguimiento de derechos colectivos se identificaron contados registros clasificados con el texto literal `2A ADICIONAL`.
- **Diagnóstico:** Conceptualmente, este hito corresponde a un ciclo `ADICIONAL` con consecutivo o ronda 2, lo cual podría simplificar el catálogo.
- **Determinación actual:** Se **mantiene como valor vigente del catálogo operativo** (`2A_ADICIONAL`) tal como se encuentra implementado en el backend y la base de datos, para no romper compatibilidad con los reportes históricos ni forzar migraciones prematuras.
- **Acción pendiente:** Queda registrado como decisión funcional para evaluación futura entre la Procuraduría Agraria y el equipo técnico.

### 15.2 Encabezado `VALIDACIÓN PA/SICT`

- **Situación:** En las hojas de derechos individuales aparecen columnas rotuladas como `VALIDACIÓN PA/SICT`.
- **Diagnóstico:** El análisis de los libros no define con certeza el actor responsable de la firma, el momento procedimental de la validación, el catálogo de resultados permitidos ni la consecuencia jurídica de su ausencia.
- **Determinación actual:** Se mantiene clasificado formalmente como `DECISIÓN FUNCIONAL REQUERIDA` y se documenta como requisito documental opcional sin bloquear el avance de los convenios ni de los pagos.
