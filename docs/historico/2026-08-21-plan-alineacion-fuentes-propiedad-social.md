# Plan de alineación de SOFTWARE-PA con las fuentes funcionales

**Fecha:** 2026-08-21

**Estado:** plan técnico; no implementado.

**Fuentes rectoras:**

- `docs/contexto/estructura_datos_propiedad_social_fuente.md`: datos que deben poder registrarse y consultarse.
- `docs/contexto/flujo_liberacion_propiedad_social_fuente.md`: orden, decisiones, bifurcaciones y convergencias del proceso.

**Documentos contextuales auditados:**

- `docs/contexto/contexto_funcional_liberacion_propiedad_social_v2.md`
- `docs/dominio/Conceptos.md`
- `docs/dominio/CONVENIOS DE OCUPACIÓN PREVIA.md`
- `docs/dominio/Introducción agraria básica.md`
- `docs/Description.md`
- `docs/Descripción proceso.md`

**Otras fuentes de corroboración:** arquitectura actual, migraciones `001` a
`028`, esquema PostgreSQL activo, modelos y schemas, routers, servicios,
frontend y pruebas automatizadas.

Este documento no modifica código ni base de datos. Las migraciones mencionadas
son conceptuales y deben implementarse sólo después de cerrar las decisiones de
la sección 13.

## Marco documental de contexto

### Jerarquía aplicable a este plan

Los documentos no son intercambiables. Para evitar que una síntesis posterior
modifique las fuentes que se deben cumplir, este plan aplica la siguiente
precedencia:

1. `flujo_liberacion_propiedad_social_fuente.md` gobierna el orden, las conexiones, las bifurcaciones y la participación institucional visible.
2. `estructura_datos_propiedad_social_fuente.md` gobierna los bloques y datos que deben poder seguirse.
3. Las decisiones funcionales aprobadas resuelven vacíos y contradicciones sin reescribir las fuentes.
4. Los seis documentos auditados a continuación explican dominio, intención o diseño previo y sirven para formular decisiones, pero no crean por sí solos requisitos obligatorios adicionales.
5. El código y la base activa demuestran la implementación actual, no el proceso objetivo.

Esta jerarquía es deliberada. `contexto_funcional_liberacion_propiedad_social_v2.md`
declara internamente a `Descripción proceso.md` como fuente funcional canónica,
pero el encargo que origina este plan designa expresamente al flujo y a la
estructura fuente como fuentes rectoras. Por tanto, las reglas adicionales de
`Descripción proceso.md` se conservan como contexto y requieren decisión
funcional cuando no estén respaldadas por las dos fuentes principales.

### Auditoría individual

| Documento | Qué es | Qué aporta al plan | Auditoría y límite de uso |
|---|---|---|---|
| `docs/contexto/contexto_funcional_liberacion_propiedad_social_v2.md` | Síntesis funcional extensa que integra el flujograma, la matriz de datos, la descripción canónica previa y el contexto agrario desde la perspectiva de seguimiento de la PA. Distingue actividad propia, actividad compartida, hito externo, dato externo y registro de seguimiento. | Proporciona una lectura transversal de Investigación, Negociación y Consolidación; explica rutas colectiva/individual, ciclos de convenios, ORV/padrón, procedencia institucional, RAN, FIFONAFE, regla económica y momento propuesto para crear la afectación. Es especialmente útil para trazabilidad y para evitar atribuir a la PA actos del RAN o FIFONAFE. | Es una interpretación consolidada, no una transcripción primaria. Mezcla requisitos fuente con decisiones de `Descripción proceso.md`, como comunidad indígena terminal, detalle de pagos, reglas específicas de modificatorios y el papel de `tramo_nucleo` como expediente maestro. Su propia jerarquía documental no gobierna este plan. También contiene una tensión interna: pide priorizar el flujo fuente ante contradicción, pero permite que la descripción funcional complete sus vacíos. Cada regla adicional debe rastrearse a su origen y pasar por D02-D10 cuando corresponda. |
| `docs/dominio/Conceptos.md` | Glosario breve de conceptos del negocio y nombres de campos: tramo, núcleo, adscripción registral, residencia, afectación, tenencia, sensibilización, caminamiento, asamblea, convenios y BDT. | Ayuda a nombrar entidades y etiquetas de UI; aclara que entidad/municipio son de adscripción registral, que residencia es la oficina regional, que el caminamiento verifica el trazo y que `monto_bdt` corresponde a bienes distintos a la tierra. Advierte sobre WGS84, UTM, zonificación y procedencia geoespacial. | No define flujo, cardinalidades, obligatoriedad ni ciclo de vida. Es incompleto y presenta redacción/normalización irregular. Afirma que el núcleo es “la entidad central” y formula la afectación en términos amplios, pero eso no resuelve el nivel técnico de expediente ni el momento de alta. No define E/C, PPT ni DGAOPR. Sus referencias a fechas de convocatoria requieren validación jurídica antes de convertirse en constraints. |
| `docs/dominio/CONVENIOS DE OCUPACIÓN PREVIA.md` | Resumen jurídico-funcional del COP y su relación con la expropiación, basado en referencias generales al artículo 27, Ley Agraria y su reglamento. Distingue ocupación con y sin convenio. | Explica la finalidad del COP, contenido general, partes y cláusulas; respalda la diferencia entre colectivo e individual, la autorización asamblearia para uso común, la firma directa con titular y la intervención de FIFONAFE/retiro de fondos en colectivos. Da contexto a las variantes y a la salida de expropiación. | Es material introductorio, no dictamen jurídico ni especificación ejecutable. No tiene versión normativa, citas detalladas ni tratamiento de excepciones. No debe usarse por sí solo para fijar plazo, quórum, obligatoriedad, gate de pago o continuidad procesal. Toda regla legal debe validarse con el área jurídica y normativa vigente. |
| `docs/dominio/Introducción agraria básica.md` | Introducción al régimen agrario mexicano: instituciones, núcleos, órganos, sujetos, tipos de tierra, acciones agrarias y expropiación. | Sustenta el vocabulario de ejido/comunidad, Asamblea, Comisariado, Consejo de Vigilancia, sujetos agrarios, uso común, parcela y asentamiento; ayuda a ubicar PA, RAN, SEDATU y FIFONAFE sin confundir responsabilidades. La vigencia de ORV sirve como hipótesis de validación. | Es un resumen formativo, no una fuente de requisitos del sistema ni una validación legal actualizada. La duración de órganos, formalidades y referencias reglamentarias no deben codificarse sin revisión jurídica. No define el flujo particular del proyecto, los datos de captura ni la arquitectura. |
| `docs/Description.md` | Visión inicial del producto: digitalizar el seguimiento antes llevado en Excel mediante dashboard/reporteador y visor geoespacial, con roles de operador, geógrafo, visualizador y administrador. | Aporta propósito, usuarios, métricas esperadas, visualización de superficie afectada/liberada, proyectos/tramos/geometrías y la necesidad de auditar ORV, sensibilización, asambleas, RAN y FIFONAFE. Sirve para priorizar consulta, mapa, reportes y UX por rol. | Es una descripción de alto nivel y anterior a la especificación detallada. Dice que las afectaciones son polígonos clasificados “desde su alta” y que, tras identificar el cruce, se registra la afectación; esa formulación puede adelantar su nacimiento respecto del flujo detallado de sensibilización, caminamiento y confirmación. No gobierna secuencia, campos ni modelo de expediente. Sus métricas deben recalcularse desde estados/evidencias, no capturarse como verdad independiente. |
| `docs/Descripción proceso.md` | Especificación funcional interna que se autodenomina canónica y expresa el modelo objetivo con nombres de entidades actuales. Describe configuración territorial, investigación, afectación confirmada, ciclos colectivos/individuales, pagos, cierre, documentos y estado de implementación. | Es la fuente contextual más concreta para diseñar: fija que una posible afectación no es aún `afectacion`, propone `tramo_nucleo` como expediente territorial, normaliza personas/ORV/titulares, detalla sensibilización/minutas, BDT, variantes, fórmula económica, pago suficiente, salidas terminales, versionado y auditoría. Sus afirmaciones permiten formular tareas y casos de prueba precisos. | Combina proceso objetivo, decisiones de diseño y afirmaciones sobre implementación. Añade requisitos no literales de las fuentes rectoras: lugar/responsable/acuerdos de actividades, quórum, detalle bancario de pagos, comunidad indígena terminal, modificatorio individual sin RAN, fórmula económica y documentación versionada. Además, algunas afirmaciones de “implementado” no prueban captura end-to-end. Debe corroborarse contra código/DB y someter sus ampliaciones a decisión funcional; no puede utilizarse para resolver automáticamente D02-D10. |

### Hallazgos cruzados de la auditoría documental

| ID | Hallazgo | Efecto en este plan |
|---|---|---|
| MC-01 | Los seis documentos coinciden en que el núcleo agrario organiza información colectiva y que la ruta individual se vincula con parcela/titular. | Refuerza conservar núcleo, parcela, persona y relaciones normalizadas; no justifica una tabla `expediente`. |
| MC-02 | El contexto v2 y `Descripción proceso.md` sitúan el alta de `afectacion` después de sensibilización, caminamiento y confirmación; `Description.md` lo resume como alta posterior al cruce. | Prevalece la reconstrucción del flujo y se mantiene D05 para definir el gate exacto. `Description.md` no se usa para adelantar el alta. |
| MC-03 | Los documentos distinguen seguimiento de PA de actos producidos por RAN, SEDATU o FIFONAFE. | Los datos externos deben conservar institución de procedencia; almacenar un dato no atribuye su generación a PA. |
| MC-04 | Los documentos de dominio respaldan la diferencia entre derechos colectivos e individuales, pero no detallan todas las variantes de la matriz fuente. | Las variantes se implementan desde la estructura fuente y contratos discriminados, no desde generalizaciones jurídicas. |
| MC-05 | `Descripción proceso.md` añade capacidades valiosas que no aparecen como campos en las fuentes rectoras: lista de actividades más rica, detalle financiero, BDT estructurado, alertas y salidas terminales. | Se conservan si ya existen y son compatibles; no se convierten en trabajo obligatorio de alineación sin decisión o requisito fuente. |
| MC-06 | Comunidad indígena es condición descriptiva en la estructura fuente, mientras que la descripción canónica previa la convierte en salida terminal. | D04 permanece abierta; no automatizar salida ni cierre. |
| MC-07 | El documento COP apoya retiro de fondos colectivo; la estructura lo registra como estatus, pero no define toda su aplicabilidad y secuencia. | D07 permanece abierta y debe validarse jurídica/funcionalmente. |
| MC-08 | El contexto v2 y `Descripción proceso.md` fijan reglas económicas y detalle de pagos que exceden la matriz fuente, aunque el sistema ya las implementa parcialmente. | Conservar integridad financiera existente; D10 decide qué es obligatorio para esta alineación. |
| MC-09 | Ningún documento contextual define E/C, PPT o DGAOPR de forma suficiente para expansión técnica. | Mantener D01 y la prohibición de inventar significados. |
| MC-10 | Los resúmenes jurídicos carecen de fecha de vigencia normativa y no sustituyen revisión legal. | Antes de codificar formalidades, plazos, quórum o efectos jurídicos se requiere validación del área jurídica. |
| MC-11 | `Descripción proceso.md` y el contexto v2 usan `tramo_nucleo` como expediente maestro, pero también ordenan validar si ese papel es correcto. | El plan conserva la entidad técnica y simplifica su exposición; no toma la etiqueta histórica como prueba arquitectónica. |
| MC-12 | Varias rutas internas de documentos citadas al final de `Descripción proceso.md` omiten hoy el subdirectorio `docs/dominio/`. | Corregir referencias documentales cuando se actualice esa fuente; no afecta el modelo funcional. |

### Uso obligatorio del contexto durante la implementación

- Cada historia de trabajo debe citar primero el requisito de flujo/dato rector y después el contexto complementario que explica su significado.
- Si una regla sólo aparece en un documento contextual, debe clasificarse como decisión aprobada, compatibilidad existente o mejora futura; nunca como requisito fuente implícito.
- Las reglas jurídicas deben incluir evidencia de revisión jurídica y fecha de vigencia antes de llegar a PostgreSQL.
- Las afirmaciones sobre “implementado” deben probarse en DB, API, UI y tests; la existencia de una tabla o campo no demuestra captura funcional.
- La terminología visible debe apoyarse en el glosario, pero corregir ambigüedades y errores sin alterar el significado registral.
- Las métricas de dashboard y mapa deben derivarse de entidades y estados auditables definidos por el flujo.

## 1. Objetivo

- **Estado actual:** el sistema dispone de una base técnica útil y trazable para proyecto, derecho de vía, tramo, núcleo, relación territorial `tramo_nucleo`, afectaciones, ciclos, actividades, asambleas, convenios, RAN, FIFONAFE, pagos, documentos y geometrías. Las reglas centrales existen, pero varios datos ya modelados no tienen captura operativa, algunos formularios envían campos incompatibles con el tipo de afectación y la interfaz no representa íntegramente el flujo fuente.
- **Estado objetivo:** ejecutar las fases Investigación, Negociación y Consolidación; capturar los campos de la estructura fuente en la entidad y momento correctos; distinguir derechos colectivos e individuales; impedir saltos inválidos; conservar trazabilidad histórica; y presentar al usuario un expediente comprensible sin exponer `tramo_nucleo` como concepto técnico.
- **Nivel de cambio requerido:** ajustes funcionales, de contratos y de UX, con endurecimiento puntual y evolutivo de PostgreSQL. No existe evidencia suficiente para crear una tabla `expediente` ni para reemplazar la arquitectura base.

La ruta mínima objetivo es:

```text
Persistencia
Proyecto -> Tramo -> tramo_nucleo -> Afectación -> Ciclo

Presentación
Proyecto -> Tramo -> Núcleo agrario -> Expediente -> Afectaciones
```

`tramo_nucleo` se conserva como relación territorial y raíz técnica de las
actuaciones compartidas. En la interfaz se presenta como **Expediente del núcleo
en el tramo**. `afectacion` representa una afectación confirmada y sus ciclos
representan el COP original y los procesos posteriores aplicables.

## 2. Brechas identificadas

| ID | Fuente | Requisito | Estado actual | Brecha | Prioridad |
|---|---|---|---|---|---|
| B-01 | Flujo, Investigación | Identificar núcleos con posible afectación por el trazo | Intersecciones geoespaciales, candidatos y `tramo_nucleo` existen | La UX mezcla candidato, relación territorial y expediente; no muestra con claridad su momento de confirmación | ALTA, obligatoria |
| B-02 | Flujo, Investigación | Registrar análisis preliminar de afectaciones | No existe un hito inequívoco; podría documentarse como actividad/minuta | Evidencia y condición de cierre no definidas por la fuente de datos | ALTA, REQUIERE DECISIÓN FUNCIONAL |
| B-03 | Flujo, Investigación | Revisar condiciones sociales, jurídicas y registrales, incluido padrón y ORV | Núcleo, ORV y padrón están modelados | No hay una vista integrada ni gate de revisión; padrón carece de UI | ALTA, obligatoria |
| B-04 | Flujo, Investigación | Registrar acercamiento inicial | Actividades genéricas sólo admiten sensibilización/caminamiento en contratos relevantes | Etapa no capturable de forma inequívoca | MEDIA, REQUIERE DECISIÓN FUNCIONAL |
| B-05 | Estructura, Sensibilización | Fecha programada y realizada | Ambas columnas existen en `actividad_campo` | UI sólo captura `fecha_realizada` | CRÍTICA, obligatoria |
| B-06 | Estructura, Caminamiento | Fecha programada y realizada | Ambas columnas existen y hay regla sensibilización -> caminamiento | UI sólo captura realizada; actividades de ciclos posteriores no quedan ligadas al ciclo desde el formulario | CRÍTICA, obligatoria |
| B-07 | Flujo, Investigación | Analizar afectaciones e identificar predios y situación jurídica antes de confirmar | `afectacion` tiene parcela, geometría y situación jurídica; al crearla nace el ciclo original | No hay checklist de confirmación; la UI puede crear una afectación con información insuficiente | ALTA, obligatoria |
| B-08 | Flujo, Negociación | Registrar Avalúo antes de separar rutas | No existe entidad o campo inequívoco | La fuente de flujo exige la etapa, pero la fuente de datos no define qué capturar | ALTA, REQUIERE DECISIÓN FUNCIONAL |
| B-09 | Estructura, Colectiva | Datos generales: entidad, municipio, residencia, consecutivo, núcleo, E/C, destino, parcela/solar | Casi todos existen o se derivan de FKs | E/C no está definido; la UI no presenta la procedencia de cada dato | ALTA; E/C requiere decisión |
| B-10 | Estructura, Individual | Tipo y número de parcela, titular, constancia, certificado y folio | `parcela`, `persona` y `parcela_titular` existen; persiste `parcela.nombre_titular` legacy | La captura no consolida todos los campos ni privilegia siempre la relación normalizada | ALTA, obligatoria |
| B-11 | Estructura, ORV | Seis cargos, vigencia, estatus y acta RAN | Campos legacy y `orv_integrante` existen; vigencia puede derivarse | No se capturan acta/documentos/número en UI; los cargos normalizados no están poblados en los datos activos | ALTA, obligatoria |
| B-12 | Estructura, Padrón | Fecha y número de ejidatarios/comuneros | `padron_historial` y API existen | No existe UI; la asamblea no permite seleccionar `id_padron` | CRÍTICA, obligatoria |
| B-13 | Flujo, Colectiva | Convocatorias y actas de no verificativo, cuando proceda | Tipos y fechas existen en `asamblea` | El formulario no expresa el caso no verificativo ni la secuencia completa de convocatorias | ALTA, obligatoria |
| B-14 | Flujo, Colectiva | Decisiones anuencia/no anuencia y acuerdo/no acuerdo | `resultado_anuencia`, conciliación y salida terminal existen parcialmente | `resultado_anuencia` se muestra en asambleas donde no aplica y no existe una transición guiada completa | ALTA, obligatoria |
| B-15 | Flujo, Colectiva | Vincular la asamblea que autoriza el COP correspondiente | FK `id_asamblea_autorizacion` y validaciones existen | La elegibilidad es demasiado genérica; puede seleccionarse una asamblea semánticamente inadecuada | ALTA, obligatoria con decisión D06 |
| B-16 | Estructura, Asambleas | Fechas de convocatorias/realización e ingreso, solicitud, calificación e inscripción RAN | Los campos existen en DB y API | No se muestran ni envían los campos RAN desde la UI | CRÍTICA, obligatoria |
| B-17 | Estructura, Convenios | Firma, 90 %, 100 %, BDT, RAN y superficie según variante | Los campos existen y el backend distingue tipos | El formulario no captura RAN y usa campos de superficie incorrectos o ausentes por variante | CRÍTICA, obligatoria |
| B-18 | Estructura, Convenios | Colectivo: original, modificatorio, adicional y obras | Tipos y ciclos existen | El formulario no captura `superficie_adicional_ha`; BDT se muestra aunque se descarta en obras | CRÍTICA, obligatoria |
| B-19 | Estructura, Convenios | Individual: original, modificatorio, ampliación y remanente | Tipos y ciclos existen | El formulario envía `superficie_real_afectada_ha`, inválida para individual, y no captura `superficie_ampliacion_ha` | CRÍTICA, obligatoria |
| B-20 | Estructura, Convenios | No perder distinción entre dato no disponible y monto cero | Hay convenios firmados con BDT nulo | No puede inferirse automáticamente que `NULL = 0`; falta regla de completitud acordada | CRÍTICA, decisión y conciliación |
| B-21 | Flujo, Consolidación | Ingreso al RAN, aviso de inscripción y verificación | Ingreso, solicitud, calificación e inscripción existen | Aviso y verificación no están separados de modo inequívoco | ALTA, REQUIERE DECISIÓN FUNCIONAL |
| B-22 | Flujo y Estructura, FIFONAFE | Integrar expediente, solicitar/verificar no conflictos, responder y pagar | Trámites, cuatro pares oficio/fecha y pagos existen | UI crea el informe directamente completo, fuerza `hay_conflictos = false` y no permite estados intermedios | CRÍTICA, obligatoria |
| B-23 | Estructura, FIFONAFE | Oficios pertenecen al informe de no conflictos | PostgreSQL exige hoy oficios para cualquier trámite completo | Al completar indemnización la UI duplica datos y la restricción ubica los oficios en el tipo incorrecto | CRÍTICA, obligatoria |
| B-24 | Estructura, FIFONAFE | Estatus programado, pendiente y completo | Campo `estatus` existe | La UI no permite seguimiento gradual de informe, indemnización o retiro | ALTA, obligatoria |
| B-25 | Flujo, Pago | Integración del expediente recibe conexiones ambiguas desde firma y aviso | Backend exige RAN antes de FIFONAFE | La fuente no permite concluir que todos los casos deban esperar la misma evidencia registral | CRÍTICA, REQUIERE DECISIÓN FUNCIONAL |
| B-26 | Estructura, Colectiva | Asamblea de retiro de fondos con estatus | Tipo de asamblea y estado financiero existen | Aplicabilidad y momento exacto deben confirmarse; UI no presenta el seguimiento como bloque fuente | ALTA, decisión D07 |
| B-27 | Estructura, Documentos | Disponibles y faltantes en afectación, ORV y etapas | Catálogo polimórfico, flags y versionado existen | UI sólo expone documentos de `tramo_nucleo` y afectación; no ORV, convenio ni hitos RAN | ALTA, obligatoria |
| B-28 | Estructura, Condiciones especiales | Expropiación, no afectación a uso común y comunidad indígena | Existen banderas en `tramo_nucleo`/núcleo y salidas terminales | Alcance territorial y efecto en el flujo no están definidos por ambas fuentes | ALTA, REQUIERE DECISIÓN FUNCIONAL |
| B-29 | Flujo, trazabilidad | Cada avance debe conservar actor, fecha y evidencia | Auditoría y bloqueo de borrado cubren las tablas operativas principales | Deben verificarse nuevas columnas, transiciones y documentos; la UI no muestra historial suficiente | ALTA, obligatoria |
| B-30 | Navegación | El usuario opera un expediente del núcleo y sus afectaciones | Rutas usan IDs técnicos y la pantalla mezcla niveles | Se expone “expediente maestro/subexpediente” y no se indica qué es común o propio de una afectación/ciclo | ALTA, ajuste UX |
| B-31 | Mapa | Estado territorial consultable | Mapa abre por `id_tramo_nucleo` | El estado se reporta fijo como `en_proceso`; no refleja vistas derivadas | ALTA, obligatoria |
| B-32 | Pruebas | Demostrar cumplimiento integral de fuentes | Buenas pruebas backend de reglas parciales; E2E funcional escaso | No hay matriz fuente -> test ni E2E de rutas colectiva/individual completas | CRÍTICA, obligatoria |

## 3. Modelo de datos objetivo

### Criterios

1. La presencia de un campo en la estructura fuente obliga a poder seguirlo, no a exigirlo durante la creación inicial.
2. La obligatoriedad se aplica en el gate que cierra la etapa correspondiente, una vez resuelta D05.
3. No se crea una tabla por cada caja del flujograma. Una etapa sin datos definidos puede representarse con actividad, minuta, documento o estado derivado si la decisión funcional lo permite.
4. Los datos derivados no se duplican: entidad y municipio se obtienen del núcleo; clave de tramo del tramo; vigencia ORV de sus fechas; liberación de las evidencias del ciclo.
5. Todo dato mutable conserva auditoría, baja lógica y procedencia. Los montos usan `NUMERIC`/`Decimal` y las superficies `NUMERIC`, nunca `float`.

| Dato | Entidad/campo objetivo | Tipo / obligatoriedad / momento | Estado actual | Acción |
|---|---|---|---|---|
| Proyecto | `proyecto` | FK obligatoria desde el contexto territorial | Existe | REUTILIZAR; no duplicar en afectación |
| Clave del tramo | `tramo.clave_tramo` | Texto, obligatoria al definir tramo | Existe | REUTILIZAR y mostrar como derivada |
| Número de tramo | `tramo_nucleo.numero_tramo` | Texto; requerido si la fuente operativa lo distingue | Existe | ACLARAR semántica frente a clave |
| Entidad y municipio | `nucleo_agrario -> municipio -> entidad_federativa` | Derivados, no editables en expediente | Existe | REUTILIZAR |
| Residencia | `nucleo_agrario.residencia` | Texto, captura/actualización del núcleo | Existe | REUTILIZAR |
| Consecutivo | `tramo_nucleo.consecutivo` | Entero, asignado al confirmar la relación | Existe | REUTILIZAR; no permitir edición arbitraria |
| Núcleo agrario | `tramo_nucleo.id_nucleo` | FK obligatoria al confirmar cruce | Existe | REUTILIZAR |
| E/C | Sin destino hasta definir significado | REQUIERE DECISIÓN FUNCIONAL | No inequívoco | NO CREAR CAMPO antes de D01 |
| Destino de superficie | `afectacion.destino_superficie` | Texto/catálogo; al confirmar afectación colectiva | Existe | REUTILIZAR y definir catálogo sólo con evidencia |
| Parcela/solar colectiva | `afectacion.no_parcela_solar` | Texto; cuando aplique | Existe | REUTILIZAR |
| Tipo y número de parcela individual | `parcela.tipo_parcela`, `parcela.no_parcela_ppt` | Tipo controlado/texto; al integrar predio | Existe | REUTILIZAR; no expandir PPT sin fuente |
| Titular | `parcela_titular.id_persona` | FK; vigente al confirmar afectación individual | Existe | PRIORIZAR; `parcela.nombre_titular` queda legacy |
| Constancia, certificado y folio | `parcela.constancia_vigencia_fecha`, `certificado_parcelario`, `folio_derechos` | Fecha/texto; antes de consolidar expediente individual | Existe | REUTILIZAR y exponer en UI |
| Geometría de derecho de vía | `franja_derecho_via` y `seccion_derecho_via` | PostGIS SRID 4326, versionada | Existe | CONSERVAR |
| Intersección tramo-núcleo | `tramo_nucleo` y `candidato_tramo_nucleo` | Relación confirmada con procedencia | Existe | CONSERVAR como entidad técnica territorial |
| Geometría/superficie preliminar | `afectacion.geometria_afectacion`, `superficie_afectada_ha` | Geometría/ha; al confirmar predio afectado | Existe | REUTILIZAR; captura cartográfica asistida |
| Situación jurídica | `afectacion.situacion_juridica` | Texto; antes de confirmar afectación | Existe | REUTILIZAR y convertir en gate sólo si D05 lo confirma |
| Tipo de afectación | `afectacion.tipo_afectacion` | `colectivo`/`individual`, obligatorio al confirmar | Existe | CONSERVAR |
| Sensibilización/caminamiento | `actividad_campo.tipo_actividad`, fechas programada/realizada, resultado | Fechas; la realizada no puede preceder a la programada si ambas existen | Existe | REUTILIZAR; corregir UI y alcance de ciclo |
| Ciclo | `afectacion_ciclo` | FK a afectación, tipo y consecutivo; nace con el proceso que representa | Existe | CONSERVAR; original automático, posteriores explícitos |
| Padrón | `padron_historial.fecha_padron`, `numero_ejidatarios_comuneros` | Fecha/entero; previo a asamblea que lo usa | Existe | REUTILIZAR; crear UI y seleccionar en asamblea |
| ORV | `orv`, `orv_integrante`, `persona` | Fechas, booleano y seis cargos; revisión durante Investigación | Existe parcialmente normalizado | REUTILIZAR y migrar gradualmente desde cargos texto |
| Asamblea | `asamblea` | Convocatorias, realización, resultado/estatus y `id_padron` | Existe | REUTILIZAR; separar campos por tipo en contratos/UI |
| RAN de asamblea | `asamblea.ingreso_ran_fecha`, `numero_solicitud_ran`, `calificacion_registral_ran`, `acta_inscripcion_fecha_ran` | Fecha/texto; captura progresiva en Consolidación | Existe | REUTILIZAR y exponer |
| Convenio y variante | `convenio.tipo_convenio`, `id_convenio_padre`, `id_ciclo_afectacion` | Tipo controlado; firma durante Negociación | Existe | CONSERVAR |
| Montos de convenio | `convenio.monto_90`, `monto_100`, `monto_bdt` | `NUMERIC(18,2)`; cierre de firma/avalúo según D05 | Existe | REUTILIZAR; no convertir nulos a cero |
| Superficies de convenio | `superficie_real_afectada_ha`, `superficie_total_ha`, `superficie_adicional_ha`, `superficie_ampliacion_ha` | `NUMERIC(12,4)`; campo permitido depende de ruta/variante | Existe | REUTILIZAR con formulario discriminado |
| RAN de convenio | `ingreso_ran_fecha`, `numero_solicitud_ingreso`, `calificacion_registral`, `convenio_inscrito_fecha_ran` | Fecha/texto; captura progresiva | Existe | REUTILIZAR y exponer |
| Aviso/verificación RAN | Campos existentes o relación nueva sólo tras D03 | Obligación pendiente | No inequívoco | DECISIÓN; no inferir fechas |
| Informe de no conflictos | `tramite_fifonafe` tipo `informe_no_conflictos` | Estatus, `hay_conflictos` y cuatro pares oficio/fecha | Existe | REUTILIZAR; oficios exclusivos de este tipo |
| Indemnización | `tramite_fifonafe` tipo `indemnizacion` | Estatus programado/pendiente/completo | Existe | REUTILIZAR; no exigir oficios duplicados |
| Pago | `pago_indemnizacion` | Monto/fecha/referencia existentes; evidencia de cierre financiero | Existe | CONSERVAR; la fuente sólo exige el nodo pago, no ampliar campos sin necesidad |
| Retiro de fondos colectivo | `asamblea.tipo_asamblea = retiro_fondos` y estado derivado | Estatus; aplicabilidad según D07 | Existe | REUTILIZAR |
| Expropiación directa | `afectacion.tipo_salida_terminal` y/o `tramo_nucleo.es_expropiacion` | Alcance por decidir | Existe con doble alcance | ACLARAR, no migrar antes de D09 |
| No afecta uso común | `tramo_nucleo.proyecto_no_afecta_uso_comun` | Booleano, momento/efecto por decidir | Existe | CONSERVAR sin automatizar salida |
| Comunidad indígena | `nucleo_agrario.comunidad_indigena` | Booleano descriptivo | Existe | CONSERVAR; no convertir en salida terminal sin D04 |
| Documentación disponible/faltante | `documentacion_soporte`, `documento_version` y estados derivados | Documentos versionados; nivel según evidencia | Existe | REUTILIZAR; no depender sólo de booleanos |
| Observaciones ORV | Campo nuevo sólo si se confirma contenido a capturar | La fuente muestra encabezado sin campos | No existe inequívoco | NO IMPLEMENTAR hasta decisión |

### Auditoría objetivo

Cada alta, modificación, baja lógica y transición debe registrar el usuario y la
transacción mediante el mecanismo actual de auditoría. Para documentos debe
conservarse además versión, hash, tamaño, nombre original y fecha de carga. Las
vistas derivadas no sustituyen la evidencia base y nunca deben convertirse en
campos editables.

## 4. Flujo funcional objetivo

```text
INVESTIGACIÓN

1. Identificación de núcleos con posible afectación
   Entrada: proyecto, trazo/franja vigente, tramos y núcleos.
   Acción: calcular/revisar candidatos y confirmar el cruce Tramo-Núcleo.
   Genera: tramo_nucleo con procedencia territorial.
   Gate: candidato resuelto por usuario autorizado.

2. Análisis preliminar de afectaciones
   Entrada: cruce confirmado y evidencia disponible.
   Acción/evidencia: pendiente de D08; no crear una tabla por defecto.
   Gate: pendiente de decisión funcional.

3. Revisión social, jurídica y registral del núcleo
   Entrada: núcleo y cruce confirmados.
   Acción: revisar residencia, padrón, ORV, vigencia y acta RAN.
   Genera: registros históricos ORV/padrón y documentos.
   Gate: información requerida disponible o faltante expresamente identificada.

4. Acercamiento inicial
   Acción/evidencia: pendiente de D08.

5. Sensibilización
   Entrada: revisión del núcleo.
   Acción: registrar fecha programada, realizada, resultado, minuta/documentos.
   Gate: realización registrada para avanzar al caminamiento.

6. Caminamiento
   Entrada: sensibilización realizada.
   Acción: registrar fechas, evidencia y resultado territorial.
   Gate: caminamiento realizado.

7. Análisis e identificación de afectaciones
   Entrada: caminamiento y geometrías.
   Acción: identificar predios, tipo de derechos, titularidad y situación jurídica.
   Genera: afectación confirmada y ciclo COP original.
   Gate: datos mínimos definidos por D05; no usar afectación como prospecto.

NEGOCIACIÓN

8. Avalúo
   Entrada: afectación confirmada.
   Acción/evidencia: pendiente de D08 y D10.
   Gate: avalúo disponible según definición funcional.
   Siguiente: bifurcación por derecho colectivo o individual.

9A. Derechos colectivos
   Convocatorias/no verificativo -> Asamblea de anuencia.
   Si existe anuencia:
     conformación del acta -> firma del COP colectivo.
   Si no existe anuencia:
     conciliación y replanteamiento -> decisión de acuerdo.
     Si existe acuerdo: conformación del acta -> firma del COP colectivo.
     Si no existe acuerdo: valoración de expropiación directa y detener la
     automatización, porque la fuente no muestra una continuación.

9B. Derechos individuales
   Asesoría sobre expropiación y COP
   -> integración del expediente individual
   -> firma del COP individual.

CONSOLIDACIÓN

10A. Derechos colectivos
    Consolidar/gestionar COP
    -> ingresar acta y COP al RAN
    -> obtener aviso de inscripción
    -> verificar inscripción.

10B. Derechos individuales
    Consolidar/gestionar COP
    -> ingresar COP al RAN
    -> obtener aviso de inscripción
    -> verificar inscripción.

11. Integración para pago
    Recibe las conexiones que la fuente muestra desde firma y aviso.
    El gate exacto no se endurece hasta resolver D02.

12. FIFONAFE y cierre
    Integrar expediente de pago
    -> acompañar pago de fondos comunes cuando aplique
    -> recibir solicitud FIFONAFE
    -> verificar información y no conflictos
    -> responder a FIFONAFE
    -> registrar pago de indemnización
    -> retiro de fondos colectivo cuando D07 confirme su aplicabilidad
    -> estado de liberación derivado.
```

### Protección de reglas

| Regla | Frontend | Backend | PostgreSQL |
|---|---|---|---|
| Sensibilización antes de caminamiento | Paso bloqueado y explicación del faltante | Validar comando | Trigger actual, conservar |
| Afectación sólo al confirmar datos | Checklist y acción explícita | Validar payload y contexto | `CHECK`/FK sólo para invariantes estables tras D05 |
| Ruta colectiva/individual | Formularios discriminados | Schemas y servicios discriminados | Checks de compatibilidad existentes |
| Ciclos posteriores | Sólo opciones aplicables | Validar tipo y precondiciones | Trigger/FK de ciclo actual |
| Asamblea colectiva válida | Selección filtrada | Validar tipo, resultado, ciclo y padrón | Trigger de coherencia fortalecido tras D06 |
| Secuencia RAN | UI progresiva | Mensajes de dominio | Trigger de orden de fechas/hitos |
| FIFONAFE/no conflictos | Estados progresivos | No permitir completar sin evidencia | Constraint exclusiva por tipo y triggers |
| Pago suficiente | Mostrar límite/pagado/saldo | Lock y validación | Funciones/triggers de migración 011, conservar |
| No regresión terminal/liberada | Ocultar acciones incompatibles | Rechazar transición | Triggers y vistas derivadas |
| Aislamiento/autorización | Ocultar fuera de alcance | `require_*_scope` y roles | FKs compuestas y contexto de auditoría |

## 5. Componentes actuales

| Componente | Acción | Justificación |
|---|---|---|
| `tramo_nucleo` | CONSERVAR | Es la relación territorial Tramo-Núcleo, conserva actuaciones previas compartidas y es una raíz técnica útil. No se justificó sustituirla por `expediente`. |
| “expediente maestro” visible | AJUSTAR | Presentar “Expediente del núcleo en el tramo”; ocultar el nombre técnico y separar visualmente lo común de las afectaciones. |
| `afectacion` | CONSERVAR Y AJUSTAR | Representa derechos/predios confirmados; debe tener un gate de creación y formularios completos por tipo. |
| `afectacion_ciclo` | CONSERVAR | Modela correctamente COP original y procesos posteriores sin duplicar afectaciones. |
| `actividad_campo` | AJUSTAR | Ya soporta fechas y ciclo; ampliar captura y asignar correctamente el nivel común o de ciclo. |
| `asamblea` | AJUSTAR | Contiene convocatorias, padrón, RAN y resultados; requiere contratos/UI por tipo y validación semántica. |
| `convenio` | AJUSTAR | El modelo cubre variantes y datos fuente; el problema principal está en formulario, completitud y RAN. |
| RAN en asamblea/convenio | REUBICAR RESPONSABILIDAD DE CAPTURA | Los campos están bien ubicados; deben salir de la invisibilidad operativa y capturarse en Consolidación. |
| `tramite_fifonafe` | AJUSTAR | Separar el informe con oficios de la indemnización y permitir estatus progresivos. |
| `pago_indemnizacion` | CONSERVAR | Proporciona evidencia financiera y la regla de suficiencia ya fue endurecida. |
| `documentacion_soporte`/`documento_version` | AJUSTAR | Mantener modelo polimórfico/versionado y ampliar UI a ORV, asambleas, convenios y trámites según soporte backend. |
| `minuta`/`acuerdo` | CONSERVAR | Son evidencia de actividades y permiten ámbito común o afectación/ciclo; no reemplazan estados canónicos. |
| `orv`, `orv_integrante`, `persona` | AJUSTAR/MIGRAR | Conservar ORV y mover gradualmente cargos de texto a integrantes normalizados con revisión de identidad. |
| `parcela.nombre_titular` | RETIRAR GRADUALMENTE | Es dato legacy; la relación auditable objetivo es `parcela_titular -> persona`. |
| `padron_historial` | CONSERVAR Y EXPONER | La estructura fuente lo exige y la asamblea ya tiene FK. |
| Modelos geoespaciales | CONSERVAR | Franja versionada, secciones, candidatos y geometrías soportan el análisis territorial; mejorar captura/consulta, no rediseñar. |
| Banderas especiales | REQUIERE DECISIÓN FUNCIONAL | Existen, pero su alcance y efecto procesal no están definidos inequívocamente. |
| Avalúo | REQUIERE DECISIÓN FUNCIONAL | Es etapa del flujo sin estructura de datos definida; no inventar entidad ni campos. |

## 6. Plan de trabajo

### Fase 0 — Consolidación, decisiones y línea base

**Objetivo:** cerrar la semántica que afecta gates y migraciones, y congelar una
línea base reproducible antes de cambiar consumidores.

| ID | Objetivo y problema | Capas/archivos | Cambio y migración | Dependencias | Pruebas y criterio de aceptación | Riesgo |
|---|---|---|---|---|---|---|
| T0.1 | Aprobar D01-D10 y distinguir obligatorio, aplicable y no aplicable | Fuentes, este plan, `docs/Arquitectura_Actual.md` | Documental; sin migración | Ninguna | Acta de decisión con responsable, fecha y efecto; no quedan decisiones bloqueantes sin dueño | ALTO |
| T0.2 | Crear matriz fuente -> entidad -> API -> UI -> prueba | `docs/evaluaciones/`, modelos, schemas, rutas, frontend, tests | Documental; sin migración | T0.1 | Cada campo fuente tiene destino o resolución “no aplica” aprobada | MEDIO |
| T0.3 | Obtener línea base de esquema, migraciones, restricciones y datos incompatibles | PostgreSQL, `backend/db/migrations/` | Sólo consultas y respaldo; sin cambio de esquema | T0.1 | Backup restorable; conteos y consultas de preflight versionados en evaluación | ALTO |
| T0.4 | Definir glosario visible | Documentación y diseño frontend | Sin DB | T0.1 | “Expediente del núcleo en el tramo”, “Afectación” y “Ciclo” tienen una definición no contradictoria | BAJO |

**Dependencias:** ninguna.

**Migración:** No.

**Pruebas:** restauración del backup en entorno aislado; comparación de versión
de esquema; revisión funcional de la matriz.

**Criterio de salida:** D01-D10 resueltas o separadas como tareas que no bloquean
las primeras expansiones; baseline y respaldo aprobados.

### Fase 1 — Contrato del modelo objetivo

**Objetivo:** convertir las fuentes y decisiones aprobadas en contratos precisos
antes de modificar la base.

| ID | Objetivo y problema | Capas/archivos | Cambio y migración | Dependencias | Pruebas y criterio de aceptación | Riesgo |
|---|---|---|---|---|---|---|
| T1.1 | Definir obligatoriedad por etapa, no por alta inicial | Especificación de API, schemas objetivo | Sin DB aún | T0.1-T0.2 | Tabla de gates con campo, aplicabilidad, error y transición | ALTO |
| T1.2 | Definir contratos discriminados de asamblea y convenio | `backend/app/schemas.py`, contrato OpenAPI objetivo | Diseño de schemas; sin migración | D05-D06 | Matriz colectiva/individual y variante sin campos incompatibles | MEDIO |
| T1.3 | Definir estados y comandos de RAN/FIFONAFE | `schemas.py`, `routers/flujo.py`, `services/flujo.py` | Diseño de transición; sin migración | D02-D03-D07 | Diagrama de estados aprobado y sin transiciones ambiguas | ALTO |
| T1.4 | Definir niveles documentales | `documentacion_soporte`, `routers/documentos.py`, UI objetivo | Reutilizar modelo; relación nueva sólo si falta un tipo respaldado | T0.2 | Cada evidencia fuente tiene nivel y política de versión | MEDIO |

**Dependencias:** Fase 0.

**Migración:** No.

**Pruebas:** ejemplos de payload válidos e inválidos por etapa; revisión de
compatibilidad hacia atrás.

**Criterio de salida:** contratos y gates aprobados; cualquier columna nueva
tiene responsabilidad, fuente y consumidor identificados.

### Fase 2 — Modelo de datos e integridad PostgreSQL

**Objetivo:** corregir invariantes que hoy contradicen la estructura fuente y
expandir sólo lo aprobado.

| ID | Objetivo y problema | Capas/archivos | Cambio y migración | Dependencias | Pruebas y criterio de aceptación | Riesgo |
|---|---|---|---|---|---|---|
| T2.1 | Hacer exclusivos del informe los cuatro pares oficio/fecha | `tramite_fifonafe`; migración conceptual `029` | Agregar constraint correcta como `NOT VALID`, validar y retirar la global después | T0.3, T1.3 | Informe completo exige evidencia aprobada; indemnización completa no exige duplicarla | ALTO |
| T2.2 | Fortalecer coherencia temporal de actividades/RAN | Triggers/checks de `actividad_campo`, `asamblea`, `convenio` | Checks `NOT VALID` y triggers sólo para reglas aprobadas | T1.1-T1.3 | Casos de fechas fuera de orden rechazados sin afectar históricos identificados | ALTO |
| T2.3 | Fortalecer variante-superficie-montos | `convenio`, migración condicional | Reusar columnas; checks por tipo tras conciliar | T1.1-T1.2 | Cada variante acepta sólo sus campos y puede cerrar la etapa cuando cumple D05 | ALTO |
| T2.4 | Agregar hitos RAN sólo si D03 lo exige | `asamblea`/`convenio` o entidad registral aprobada | Expansión nullable, auditoría, índices/FKs | D03 | Aviso y verificación distinguibles sin reinterpretar datos previos | ALTO |
| T2.5 | Asegurar auditoría y no borrado de cualquier expansión | Funciones/triggers de auditoría | Triggers y política de baja lógica | T2.1-T2.4 | Insert/update/delete lógico queda registrado con usuario | MEDIO |

**Dependencias:** Fases 0 y 1; respaldo restorable.

**Migración:** Sí, evolutiva y no destructiva.

**Pruebas:** SQL transaccionales, preflight sobre datos actuales, pruebas de
restricciones `NOT VALID`/`VALIDATE`, restauración y rollback de despliegue.

**Criterio de salida:** esquema expandido compatible; ninguna restricción nueva
invalida datos sin reporte; integridad demostrada en PostgreSQL.

### Fase 3 — Backend y contratos API

**Objetivo:** exponer todos los datos ya modelados, aplicar validaciones de
dominio claras y preservar compatibilidad durante la transición.

| ID | Objetivo y problema | Capas/archivos | Cambio y migración | Dependencias | Pruebas y criterio de aceptación | Riesgo |
|---|---|---|---|---|---|---|
| T3.1 | Completar API de ORV y padrón | `models.py`, `schemas.py`, `main.py` o routers dedicados, `services/personas.py` | Sin DB salvo expansión aprobada | Fase 2 | CRUD autorizado, histórico consultable, integrantes y padrón recuperables | MEDIO |
| T3.2 | Exponer actividades por ámbito común/ciclo | `schemas.py`, endpoints de actividades, `services/flujo.py` | Sin DB | T1.1 | Payload conserva `id_ciclo_afectacion`, fechas y contexto; aislamiento validado | ALTO |
| T3.3 | Implementar schemas discriminados de asamblea/convenio | `schemas.py`, rutas actuales, `services/flujo.py` | Sin DB | T1.2, Fase 2 | API rechaza campos de otra variante con mensaje de dominio | ALTO |
| T3.4 | Exponer actualización progresiva RAN | Rutas de asambleas/convenios y servicios | Sin DB adicional | T1.3, Fase 2 | Se pueden guardar ingreso, solicitud, calificación e inscripción sin completar todo de una vez | MEDIO |
| T3.5 | Separar comandos FIFONAFE | `routers/flujo.py`, `services/flujo.py`, `schemas.py` | Sin DB adicional | T2.1 | Crear/programar, registrar oficios, resolver conflictos y completar son acciones auditables distintas | ALTO |
| T3.6 | Exponer documentos por entidad soportada | `routers/documentos.py`, `services/documentos.py`, schemas | Sin DB salvo tipo aprobado | T1.4 | ORV/convenio/asamblea/trámite admiten consulta/carga con control de alcance | ALTO |
| T3.7 | Mantener compatibilidad temporal | Schemas/rutas y OpenAPI | Aceptar contratos anteriores sólo donde no violen reglas; advertir deprecación | T3.1-T3.6 | Consumidores antiguos no pierden lectura; escrituras inválidas nunca se aceptan | MEDIO |

**Dependencias:** Fases 1 y 2.

**Migración:** No adicional; consume el esquema expandido.

**Pruebas:** unitarias de servicios, API por rol y ámbito, validación Pydantic,
errores 409/422 de dominio, OpenAPI y regresión completa.

**Criterio de salida:** todos los datos fuente modelados tienen una API
consultable y, cuando procede, una operación de captura validada.

### Fase 4 — Flujo y reglas de negocio

**Objetivo:** convertir la secuencia fuente en un flujo ejecutable sin inventar
transiciones donde el diagrama es ambiguo.

| ID | Objetivo y problema | Capas/archivos | Cambio y migración | Dependencias | Pruebas y criterio de aceptación | Riesgo |
|---|---|---|---|---|---|---|
| T4.1 | Formalizar confirmación de `tramo_nucleo` | Servicios territoriales, candidatos, endpoints | Sin tabla `expediente`; reutilizar relación | T1.1 | Un candidato puede confirmarse/rechazarse con procedencia y auditoría | MEDIO |
| T4.2 | Formalizar creación de afectación confirmada | `services/afectaciones.py`, schemas, rutas | Sin nueva tabla | D05, T3.2 | No nace como prospecto; al confirmarse crea exactamente un ciclo original | ALTO |
| T4.3 | Implementar gates Investigación -> Negociación | `services/flujo.py`, vistas de estado | Migración sólo si D08 crea evidencia explícita | D08, T3 | Sensibilización/caminamiento/identificación se respetan; avalúo sólo según decisión | ALTO |
| T4.4 | Implementar bifurcación colectiva | Servicios de asamblea/convenio/salida terminal | Sin DB salvo checks Fase 2 | D06-D09 | Anuencia, conciliación y no acuerdo conducen sólo a destinos de la fuente | CRÍTICO |
| T4.5 | Implementar ruta individual sin asamblea obligatoria | Servicios de convenio | Sin DB | T3.3 | Integración/firma individual no hereda gates colectivos | ALTO |
| T4.6 | Implementar consolidación RAN | Servicios y vistas derivadas | Consume hitos aprobados | D03, T3.4 | Ingreso, aviso/verificación e inscripción avanzan en orden aprobado | ALTO |
| T4.7 | Implementar convergencia de pago | FIFONAFE/pagos/estado | Sin endurecer antes de D02 | D02, T3.5 | Todas y sólo las entradas aprobadas pueden integrar pago | CRÍTICO |
| T4.8 | Derivar liberación | Vistas `vw_afectacion_*_estado`, servicios | Actualizar vistas sólo si decisiones cambian regla | D07, T4.7 | Liberación coincide con evidencia RAN/FIFONAFE/pago y retiro aplicable | CRÍTICO |

**Dependencias:** Fases 1 a 3 y decisiones D02-D09 pertinentes.

**Migración:** Condicional para vistas/triggers; no destructiva.

**Pruebas:** máquinas de estados, transiciones negativas, concurrencia, no
regresión, rutas colectiva/individual y salidas terminales.

**Criterio de salida:** ninguna ruta puede saltar un gate aprobado y ninguna
regla adicional se atribuye a la fuente sin decisión documentada.

### Fase 5 — Formularios y UX del proceso

**Objetivo:** permitir la captura real de los datos fuente y guiar al usuario
con contexto, pendientes y siguiente acción.

| ID | Objetivo y problema | Capas/archivos | Cambio y migración | Dependencias | Pruebas y criterio de aceptación | Riesgo |
|---|---|---|---|---|---|---|
| T5.1 | Reorganizar navegación del expediente | `App.jsx`, `ExpedientesList.jsx`, `ExpedienteDetail.jsx`, `AfectacionSubexpediente.jsx`, `Mapa.jsx` | Sin DB; conservar rutas compatibles/redirects | T0.4, T4 | Usuario llega Proyecto -> Tramo -> Núcleo -> Expediente -> Afectación sin ver IDs técnicos | MEDIO |
| T5.2 | Crear cabecera y stepper de estado | Pantallas de expediente/afectación | Sin DB | T4 | Muestra dónde está, qué falta, qué puede hacer y por qué está bloqueado | MEDIO |
| T5.3 | Completar actividades por contexto | `FlujoLiberacionPanel.jsx` o componentes extraídos | Sin DB | T3.2 | Captura programada/realizada/resultado y ciclo correcto | ALTO |
| T5.4 | Completar ORV y padrón | `OrvPanel.jsx`, nuevo panel/form de padrón, `FormAsamblea.jsx` | Sin DB | T3.1 | Seis cargos normalizados, acta, vigencia, docs y padrón seleccionable | ALTO |
| T5.5 | Corregir asambleas | `FormAsamblea.jsx` | Sin DB | T3.3-T4.4 | Campos visibles dependen del tipo; RAN y padrón capturables; anuencia sólo donde aplica | ALTO |
| T5.6 | Rehacer convenio como formulario discriminado | `FormConvenio.jsx` | Sin DB | T3.3 | Colectivo/individual y cada variante envían exactamente superficie, montos y vínculos permitidos | CRÍTICO |
| T5.7 | Crear captura RAN progresiva | Paneles de asamblea/convenio | Sin DB | T3.4-T4.6 | Ingreso, solicitud, calificación e inscripción editables y consultables | CRÍTICO |
| T5.8 | Corregir FIFONAFE | `FlujoLiberacionPanel.jsx`, `PagosPanel.jsx` | Sin DB | T3.5-T4.7 | No se fuerza “sin conflictos”; estados y oficios se registran gradualmente; indemnización no duplica oficios | CRÍTICO |
| T5.9 | Mejorar geometría de afectación | `AfectacionGeometryField.jsx`, mapa | Sin cambio de modelo | Fase 7 puede ampliar | Captura/visualización válida sin depender de WKT manual como flujo principal | MEDIO |

**Dependencias:** backend de Fases 3 y 4.

**Migración:** No.

**Pruebas:** unitarias de validadores/formularios, React Testing Library si se
incorpora, E2E con Playwright, accesibilidad básica y viewports escritorio/móvil.

**Criterio de salida:** todos los campos obligatorios de la matriz pueden
capturarse en la etapa correcta y reaparecen tras recargar; no se envían campos
ocultos o incompatibles.

### Fase 6 — Documentación y expedientes

**Objetivo:** hacer consultable la evidencia disponible/faltante en el nivel
correcto y conservar versiones.

| ID | Objetivo y problema | Capas/archivos | Cambio y migración | Dependencias | Pruebas y criterio de aceptación | Riesgo |
|---|---|---|---|---|---|---|
| T6.1 | Definir catálogo mínimo de evidencia respaldado por fuentes | Configuración/catálogos, documentación | Sin tabla nueva salvo justificación | T1.4 | Cada tipo tiene nivel, aplicabilidad y criticidad | MEDIO |
| T6.2 | Extender UI documental | `DocumentosPanel.jsx`, paneles ORV/asamblea/convenio/FIFONAFE | Sin DB | T3.6 | Carga, consulta y faltantes visibles en el expediente correcto | ALTO |
| T6.3 | Habilitar versiones reales | API/documentos/almacenamiento, `documento_version` | Reutilizar tabla actual | T3.6 | Nueva versión conserva anteriores y verifica hash | ALTO |
| T6.4 | Integrar minutas/acuerdos como evidencia de actuación | `MinutasPanel.jsx`, servicios | Sin DB | T5.3 | Minuta común o de ciclo no cruza afectaciones y enlaza la actividad correcta | MEDIO |

**Dependencias:** Fases 1, 3 y 5.

**Migración:** No, salvo relación documental aprobada no soportada hoy.

**Pruebas:** autorización, aislamiento, versionado, hash, archivos faltantes,
baja lógica y descarga.

**Criterio de salida:** disponible/faltante se deriva de evidencia consultable y
ningún documento se pierde al actualizarlo.

### Fase 7 — Geoespacial

**Objetivo:** conectar el análisis territorial con el expediente sin alterar la
arquitectura PostGIS ya validada.

| ID | Objetivo y problema | Capas/archivos | Cambio y migración | Dependencias | Pruebas y criterio de aceptación | Riesgo |
|---|---|---|---|---|---|---|
| T7.1 | Mostrar procedencia del cruce | Servicios GIS, candidatos, mapa | Sin DB si campos actuales bastan | T4.1 | Expediente muestra franja/sección/fuente que originó el cruce | MEDIO |
| T7.2 | Corregir estado del mapa | Endpoint de mapa, vistas derivadas, `Mapa.jsx` | Sin DB | T4.8 | El color/estado coincide con la vista de expediente, no es fijo | ALTO |
| T7.3 | Capturar/revisar geometría de afectación | `AfectacionGeometryField.jsx`, servicios GIS | Sin DB | T5.9 | Geometría válida SRID 4326, dentro del contexto y auditable | ALTO |
| T7.4 | Probar aislamiento espacial | PostGIS y autorización territorial | Sin DB | T7.1-T7.3 | Un usuario sólo consulta/edita geometrías de su alcance | CRÍTICO |

**Dependencias:** Fases 4 y 5.

**Migración:** No prevista.

**Pruebas:** `ST_IsValid`, SRID/tipo, intersecciones, casos vacíos, rendimiento,
autorización y pruebas visuales de mapa.

**Criterio de salida:** la evidencia espacial es reproducible, válida y coherente
con la navegación y el estado funcional.

### Fase 8 — Migración y conciliación de datos existentes

**Objetivo:** hacer compatibles los datos activos sin fabricar evidencia.

| ID | Objetivo y problema | Capas/archivos | Cambio y migración | Dependencias | Pruebas y criterio de aceptación | Riesgo |
|---|---|---|---|---|---|---|
| T8.1 | Ejecutar reportes de calidad | SQL versionado en evaluación/script operativo | Sólo lectura al inicio | Fases 2-4 | Universo clasificado como automático/manual/no inferible | MEDIO |
| T8.2 | Poblar valores inequívocos | Migración de datos idempotente | UPDATE auditable por clave exacta | T8.1 | Antes/después conciliado; segunda ejecución no cambia datos | ALTO |
| T8.3 | Preparar cola de revisión manual | Reporte CSV/administrativo con IDs estables | Sin corrección automática | T8.1 | Cada caso tiene evidencia, responsable y resolución | ALTO |
| T8.4 | Bloquear cierres incompatibles no resueltos | Backend/DB | Gate temporal, no baja ni reemplazo | T8.1 | Registros ambiguos siguen consultables pero no avanzan silenciosamente | ALTO |
| T8.5 | Validar constraints diferidas | PostgreSQL | `VALIDATE CONSTRAINT` tras conciliación | T8.2-T8.4 | Cero violaciones y conteos conservados | CRÍTICO |

**Dependencias:** expansiones desplegadas y consumidores compatibles.

**Migración:** Sí, de datos; idempotente, auditable y reversible por nueva
corrección, no por borrado histórico.

**Pruebas:** dry run, conteos, hashes/reconciliación, idempotencia, datos activos
e históricos y prueba de restauración.

**Criterio de salida:** toda fila incompatible está corregida con evidencia,
marcada para revisión o bloqueada; ninguna fue inferida por aproximación.

### Fase 9 — Pruebas integrales y UAT

**Objetivo:** demostrar trazabilidad fuente -> comportamiento y obtener
aceptación funcional antes de contraer legacy.

| ID | Objetivo y problema | Capas/archivos | Cambio y migración | Dependencias | Pruebas y criterio de aceptación | Riesgo |
|---|---|---|---|---|---|---|
| T9.1 | Completar unit/API/SQL | `backend/tests/`, migraciones | Sin esquema nuevo | Fases 2-8 | Cobertura de cada gate y cada dato fuente |
| T9.2 | E2E colectiva | `frontend/tests/e2e/` | Sin DB | Fases 5-8 | Desde cruce hasta pago/retiro, incluidos rechazo y conciliación |
| T9.3 | E2E individual | `frontend/tests/e2e/` | Sin DB | Fases 5-8 | Desde predio/titular hasta pago sin asamblea colectiva |
| T9.4 | Seguridad y aislamiento | Backend, frontend, DB | Sin DB | T9.1-T9.3 | Roles y scopes impiden cruces entre expedientes/afectaciones |
| T9.5 | UAT con casos fuente | Guiones UAT y evidencia | Sin DB | Todas | Usuarios validan captura, consulta, pendientes y siguientes acciones | ALTO |

**Dependencias:** Fases 2 a 8 terminadas.

**Migración:** No.

**Pruebas:** todas las categorías de la sección 11.

**Criterio de salida:** suite verde, matriz fuente cubierta y UAT firmado sin
defectos críticos o altos abiertos.

### Fase 10 — Contracción de elementos legacy

**Objetivo:** retirar consumidores redundantes sólo después de demostrar que el
modelo nuevo está poblado y estable.

| ID | Objetivo y problema | Capas/archivos | Cambio y migración | Dependencias | Pruebas y criterio de aceptación | Riesgo |
|---|---|---|---|---|---|---|
| T10.1 | Dejar de escribir cargos ORV texto | API/UI/modelos | Compatibilidad de lectura temporal | T8.2, T9 | 100 % de ORV aplicables usa integrantes normalizados o está en revisión | ALTO |
| T10.2 | Dejar de escribir `parcela.nombre_titular` | API/UI | Compatibilidad de lectura temporal | T8.2, T9 | Toda titularidad activa usa `parcela_titular` o está bloqueada | ALTO |
| T10.3 | Retirar rutas/labels legacy | React Router, frontend, API | Redirects/deprecación antes de borrar | T9 | Sin consumidor observado durante ventana acordada | MEDIO |
| T10.4 | Evaluar retiro físico | PostgreSQL/modelos | Migración posterior independiente | T10.1-T10.3 | Backup, cero consumidores y aprobación explícita | CRÍTICO |

**Dependencias:** UAT y periodo de compatibilidad.

**Migración:** Sí, sólo en una entrega posterior y nunca como primer paso.

**Pruebas:** regresión completa, restauración, análisis de consumidores y
comparación de datos.

**Criterio de salida:** legacy sin consumidores y trazabilidad preservada. El
retiro físico no forma parte del cumplimiento inicial de las fuentes.

## 7. Migraciones propuestas

Los nombres son conceptuales y deben ajustarse al alcance aprobado. La siguiente
migración disponible es `029`; no se debe reservar un número hasta implementar.

| Orden | Migración conceptual | Tipo | Dependencias | Riesgo |
|---|---|---|---|---|
| 1 | Preflight y respaldo restorable | Línea base, sin DDL | Fase 0 | ALTO si se omite |
| 2 | `029_fifonafe_oficios_por_tipo_expand` | EXPAND: constraint correcta `NOT VALID`, funciones compatibles | D02 y diseño Fase 1 | ALTO |
| 3 | Validación de la constraint nueva | VALIDATE | Conciliación de casos incompatibles | MEDIO |
| 4 | Despliegue backend compatible con ambas reglas | Compatibilidad | Migración 029 | MEDIO |
| 5 | `030_fifonafe_retirar_constraint_global` | CONTRACT limitado: retirar sólo `chk_estatus_completo_requiere_oficios` cuando no tenga consumidores | Backend compatible y constraint validada | ALTO |
| 6 | `031_convenio_completitud_fuente` | EXPAND/fortalecimiento condicional por variante | D05, conciliación de nulos | ALTO |
| 7 | `032_asamblea_coherencia_fuente` | EXPAND/fortalecimiento condicional | D06 y datos conciliados | ALTO |
| 8 | `033_hitos_registrales` | EXPAND nullable, sólo si D03 exige datos separados | D03 | ALTO |
| 9 | Migraciones idempotentes de conciliación | DATA | Reportes Fase 8 | ALTO |
| 10 | `034_contraccion_legacy` | CONTRACT diferido | Fase 10 y aprobación explícita | CRÍTICO |

Secuencia obligatoria:

```text
expandir
-> desplegar compatibilidad
-> poblar/conciliar
-> validar
-> cambiar consumidores
-> observar
-> retirar legacy en una entrega posterior
```

Cada migración debe incluir preflight, transacción cuando sea posible, códigos
de error de dominio, actualización de vistas/funciones dependientes, auditoría y
pruebas en una copia representativa. No debe convertir `NULL` a cero ni hacer
`DELETE` físico.

## 8. Cambios backend

| Cambio | Servicio/Router/Schema | Fase |
|---|---|---|
| Contratos de completitud por etapa | `backend/app/schemas.py`, servicios de dominio | 1, 3 y 4 |
| Confirmación territorial y procedencia | servicios de núcleos/importación/afectaciones y endpoints actuales | 4 |
| Actividades comunes y por ciclo | endpoints actuales, `services/flujo.py`, `schemas.py` | 3 y 4 |
| ORV normalizada y padrón histórico | `main.py` o router dedicado, `services/personas.py`, schemas | 3 |
| Asamblea discriminada y RAN progresivo | endpoints de asamblea, `services/flujo.py`, schemas | 3 y 4 |
| Convenio discriminado por ruta/variante | endpoints de convenio, `services/flujo.py`, schemas | 3 y 4 |
| Hitos de aviso/verificación | servicio/contrato aprobado en D03 | 2 a 4 |
| Estados y comandos FIFONAFE | `backend/app/routers/flujo.py`, `backend/app/services/flujo.py`, schemas | 3 y 4 |
| Regla de integración de pago | `services/flujo.py`, `routers/pagos.py`, vistas de estado | 4 |
| Documentos por nivel y versión | `routers/documentos.py`, `services/documentos.py`, schemas | 3 y 6 |
| Minutas por ámbito correcto | `routers/minutas.py`, `services/minutas.py` | 6 |
| Estado real para mapa | endpoint de mapa y vistas derivadas | 7 |
| Autorización y auditoría de nuevos comandos | `services/access.py`, contexto de auditoría | Todas |

## 9. Cambios frontend

| Vista/Formulario | Cambio | Fase |
|---|---|---|
| `ExpedientesList.jsx` | Navegar por Proyecto -> Tramo -> Núcleo y mostrar “Expediente” | 5 |
| `ExpedienteDetail.jsx` | Cabecera territorial; separar actuaciones comunes de afectaciones | 5 |
| `AfectacionSubexpediente.jsx` | Mostrar ruta colectiva/individual, ciclo activo, pendientes y siguiente acción | 5 |
| `App.jsx` / React Router | Conservar deep links y añadir redirects/URLs comprensibles sin romper IDs internos | 5 y 10 |
| `Mapa.jsx` | Abrir el mismo expediente y mostrar estado derivado real | 5 y 7 |
| `FlujoLiberacionPanel.jsx` | Extraer formularios por etapa; no fijar ciclo, contexto, estatus o ausencia de conflicto | 5 |
| Formulario de actividad | Capturar programada, realizada, resultado, nivel y ciclo | 5 |
| `OrvPanel.jsx` | Capturar/editar seis cargos, vigencia, acta RAN y documentos | 5 y 6 |
| Panel de padrón | Alta/edición/consulta histórica y selección desde asamblea | 5 |
| `FormAsamblea.jsx` | Campos por tipo, convocatorias, padrón, resultado y RAN progresivo | 5 |
| `FormConvenio.jsx` | Formularios discriminados y superficies/montos/RAN correctos | 5 |
| `PagosPanel.jsx` | Límite, pagado, saldo y estado; integración según D02 | 5 |
| `DocumentosPanel.jsx` | Selección de nivel, evidencia disponible/faltante y versiones | 6 |
| `MinutasPanel.jsx` | Contexto común o ciclo claramente visible | 6 |
| `AfectacionGeometryField.jsx` | Editor cartográfico asistido y validación visible | 5 y 7 |

## 10. Conciliación de datos existentes

### Automática

- Derivar vigencia ORV de `inicio_vigencia` y `fin_vigencia` respecto de la fecha de consulta; no persistir un booleano duplicado.
- Derivar entidad, municipio, proyecto, clave de tramo y núcleo por FKs existentes.
- Detectar duplicación exacta de oficios entre informe de no conflictos e indemnización; sólo copiar/reubicar cuando los IDs, valores y ciclo prueben inequívocamente el origen.
- Generar reportes de faltantes por tipo de convenio, afectación y ciclo sin completar valores.
- Reutilizar superficie de un convenio del mismo ciclo únicamente cuando la relación y el tipo determinen de forma inequívoca el campo objetivo.
- Poblar relaciones desde claves técnicas exactas ya existentes; nunca desde coincidencia aproximada.

### Manual

- Resolver los convenios firmados con `monto_bdt IS NULL` mediante evidencia documental; no asumir cero.
- Conciliar cargos ORV de texto con `persona`/`orv_integrante`, validando identidad y cargo.
- Conciliar `parcela.nombre_titular` con `parcela_titular` y `persona`.
- Vincular padrones históricos con asambleas usando evidencia del expediente.
- Completar superficies de adicional/ampliación/remanente cuando el formulario anterior no las capturó.
- Revisar banderas de expropiación, no afectación a uso común y comunidad indígena tras definir su alcance.
- Separar aviso y verificación RAN sólo si existen documentos que acrediten fechas distintas.

### No inferible

- Identidad de una persona por nombre similar.
- `monto_bdt NULL = 0`.
- Padrón aplicable por ser el más cercano en fecha.
- Aviso de inscripción a partir de la fecha de inscripción.
- Salida terminal por comunidad indígena a partir del booleano descriptivo.
- Alcance de expropiación entre `tramo_nucleo` y una afectación concreta.
- Vínculo documental por nombre de archivo, carpeta o proximidad temporal.
- Condición E/C, significado de PPT o contenido de DGAOPR no explicado por las fuentes.

Los casos no inferibles deben permanecer consultables, marcados para revisión y
bloqueados sólo en el gate que requiera ese dato. No deben impedir la consulta
del historial ni corregirse silenciosamente.

## 11. Pruebas

| Fase | Pruebas obligatorias | Gate |
|---|---|---|
| 0 | Backup/restauración, snapshot de esquema y conteos, revisión funcional | Línea base reproducible y decisiones con dueño |
| 1 | Casos de contrato válidos/inválidos por etapa, ruta y variante | Contratos aprobados sin campos huérfanos |
| 2 | SQL de checks, triggers, FKs, `NOT VALID`/`VALIDATE`, auditoría y datos legacy | Integridad nueva sin pérdida de filas |
| 3 | Unitarias de servicios, API, schemas, roles, scopes, serialización y compatibilidad | Todo dato fuente puede escribirse/consultarse por API |
| 4 | Secuencia positiva y negativa, concurrencia, no regresión, estados derivados | Ningún salto inválido; rutas no se contaminan |
| 5 | Componentes/formularios, payload real, recarga, errores y E2E de navegación | Captura completa desde UI sin campos descartados |
| 6 | Carga, versión, hash, descarga, aislamiento y faltantes documentales | Evidencia íntegra y recuperable |
| 7 | PostGIS: SRID, tipo, validez, intersección, autorización y mapa | Geometría/estado coherentes y no vacíos |
| 8 | Dry run, idempotencia, conteos, reconciliación y bloqueo de ambiguos | 100 % de incompatibles clasificado |
| 9 | Flujos completos colectivo/individual, autorización, regresión y UAT | Suite verde y UAT sin críticos/altos |
| 10 | Análisis de consumidores, lectura legacy, rollback/restauración | Cero consumidores antes de retirar |

Matriz mínima de escenarios end-to-end:

1. Colectiva con anuencia, COP, RAN, no conflictos, pago y retiro aplicable.
2. Colectiva sin anuencia, conciliación con acuerdo y convergencia al COP.
3. Colectiva sin acuerdo, salida a valoración de expropiación sin continuación inventada.
4. Individual con titular/parcela, COP, RAN, no conflictos y pago, sin asamblea colectiva.
5. Ciclo colectivo de superficie adicional con sensibilización, caminamiento, asamblea y convenio correctos.
6. Ciclo colectivo de obras complementarias sin BDT si así lo define la estructura.
7. Ciclos individuales de ampliación y ampliación remanente con superficie correcta.
8. Intentos de cruzar `tramo_nucleo`, afectación, ciclo, documento o pago entre expedientes.
9. Intentos de avanzar con dato faltante, conflicto, RAN fuera de orden o pago insuficiente.
10. Datos legacy ambiguos consultables, pero sin completar etapas automáticamente.

## 12. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Endurecer una secuencia que el flujograma deja ambigua | ALTA | CRÍTICO | Resolver D02 y conservar compatibilidad hasta UAT |
| Convertir campos presentes en obligatorios demasiado pronto | ALTA | ALTO | Obligatoriedad por gate, preflight y D05 |
| Pérdida de historia al normalizar titulares/ORV | MEDIA | CRÍTICO | Expand/contract, `persona_fuente_legacy`, revisión manual y no borrado |
| Cambiar estados derivados de expedientes activos | MEDIA | CRÍTICO | Comparativa antes/después y conciliación previa a validar |
| Formularios discriminados envían campos ocultos | ALTA | ALTO | Construir payload por variante y pruebas de contrato/E2E |
| Duplicar o atribuir mal evidencia RAN/FIFONAFE | MEDIA | ALTO | IDs/ciclos exactos, versionado documental y no inferencia temporal |
| Condiciones de carrera en pagos/cierres | MEDIA | CRÍTICO | Locks existentes, triggers y pruebas concurrentes |
| Romper deep links del mapa/expedientes | MEDIA | MEDIO | Rutas compatibles y redirects durante observación |
| Aislamiento insuficiente en endpoints nuevos | MEDIA | CRÍTICO | Helpers de scope, FKs compuestas y matriz por rol |
| Migración 029 invalida históricos | MEDIA | ALTO | Constraint `NOT VALID`, reporte y validación posterior |
| Crear entidades para etapas sin datos fuente | MEDIA | MEDIO | Exigir responsabilidad, dato y ciclo de vida antes de DDL |
| UAT descubre interpretación distinta de E/C, avalúo o retiro | ALTA | ALTO | Cerrar decisiones en Fase 0 antes de gates irreversibles |

## 13. Decisiones funcionales pendientes

| ID | Decisión | Motivo | Bloquea |
|---|---|---|---|
| D01 | Definir qué significa E/C y si es dato, clasificación o derivado | La fuente lo nombra pero no lo desarrolla | Campo/visualización de datos generales |
| D02 | Definir cuándo puede iniciar la integración para pago y qué evidencia RAN es gate | El flujograma muestra entradas desde firma y aviso con geometría ambigua | Regla FIFONAFE y Fase 4.7 |
| D03 | Determinar si aviso de inscripción y verificación requieren datos separados de ingreso/calificación/inscripción | El flujo los separa; la estructura no define campos propios | Migración 033, API y UI RAN |
| D04 | Definir alcance procesal de comunidad indígena y no afectación de uso común | La estructura los lista; el flujo no los convierte en salidas | Estados terminales y UX |
| D05 | Definir campos mínimos al confirmar afectación, firmar convenio y cerrar RAN | La estructura exige seguimiento, no obligatoriedad al alta | Checks, schemas y gates |
| D06 | Definir qué tipos/resultados de asamblea autorizan cada convenio colectivo, especialmente tras conciliación | La fuente describe la secuencia pero no codifica tipos técnicos | Triggers y validación de COP |
| D07 | Definir cuándo aplica la asamblea de retiro de fondos colectivo | La estructura la incluye, pero debe confirmarse la regla de cierre | Estado financiero/liberación |
| D08 | Definir evidencia mínima para análisis preliminar, acercamiento y Avalúo | Son nodos del flujo sin campos en la estructura | Modelo/actividad y gate Investigación -> Negociación |
| D09 | Definir si expropiación directa es decisión por afectación o por todo el cruce Tramo-Núcleo | El modelo actual mantiene ambas posibilidades | Migración, salida terminal y estados |
| D10 | Definir si el detalle de pagos más allá del nodo/estatus fuente forma parte obligatoria de esta alineación | El sistema ya posee más detalle que la fuente principal | Alcance de formularios/reportes financieros |

Una decisión debe incluir: opción elegida, evidencia, responsable funcional,
fecha, entidades afectadas, transición, dato obligatorio y tratamiento de
históricos. “Se resolverá en desarrollo” no cierra la decisión.

## 14. Orden exacto recomendado

1. Aprobar este plan como baseline técnico, sin iniciar DDL.
2. Resolver D01-D10 con responsables funcionales.
3. Construir y aprobar la matriz fuente -> dato -> entidad -> API -> UI -> prueba.
4. Generar respaldo restorable y snapshot del esquema/datos activos.
5. Ejecutar preflight de RAN, convenios, FIFONAFE, pagos, ORV, padrón, documentos y titulares.
6. Definir contratos y gates por etapa/ruta/variante.
7. Implementar y probar la expansión FIFONAFE `029` con constraint `NOT VALID`.
8. Desplegar backend compatible con la regla nueva y la anterior.
9. Implementar las expansiones condicionales de convenio, asamblea e hitos RAN aprobadas.
10. Añadir auditoría, índices, FKs y tests SQL de cada expansión.
11. Completar APIs de ORV, padrón, actividades, asambleas, convenios, RAN y FIFONAFE.
12. Implementar schemas discriminados y errores de dominio.
13. Implementar confirmación de afectación y gates de Investigación.
14. Implementar bifurcaciones colectiva/individual y consolidación RAN.
15. Implementar la convergencia a pago aprobada y recalcular estados derivados.
16. Reorganizar navegación y terminología del expediente.
17. Corregir primero los formularios críticos: convenio, asamblea, actividades y FIFONAFE.
18. Incorporar ORV, padrón, documentos y minutas al flujo visible.
19. Corregir mapa, procedencia territorial y captura geoespacial.
20. Ejecutar conciliación automática idempotente.
21. Resolver o bloquear explícitamente los casos de revisión manual/no inferible.
22. Validar constraints diferidas y comparar estados/conteos.
23. Ejecutar suite completa, E2E colectiva/individual, seguridad y UAT.
24. Observar compatibilidad y eliminar escrituras legacy.
25. Evaluar contracción física en una entrega posterior independiente.

El primer incremento desplegable debe cerrar B05, B06, B12, B16, B17-B19 y
B22-B23: hoy son los puntos donde la base ya tiene capacidad, pero el usuario no
puede capturarla correctamente o el formulario envía información inválida.

## 15. Qué NO debe implementarse todavía

1. Una tabla `expediente` sólo para sustituir el nombre visible de `tramo_nucleo`.
2. La eliminación o recreación de `tramo_nucleo`.
3. La creación de tablas para análisis preliminar, acercamiento, Avalúo, aviso o verificación antes de D03/D08.
4. La conversión automática de `NULL` a cero en montos BDT u otros importes.
5. La asociación de personas, padrones, documentos o hitos por nombre o cercanía temporal.
6. La salida terminal automática de comunidades indígenas o de casos sin uso común afectado.
7. La imposición de RAN-before-FIFONAFE más estricta o más laxa sin D02.
8. La eliminación de cargos ORV texto, `parcela.nombre_titular`, rutas o columnas legacy durante la expansión.
9. La ampliación de E/C, PPT o DGAOPR con significados no definidos en las fuentes.
10. Refactors generales de autenticación, importación o diseño visual que no sean necesarios para esta alineación.

## 16. Definición de terminado

SOFTWARE-PA puede declararse alineado sólo cuando se cumplan simultáneamente las
siguientes condiciones:

### Cobertura de datos

- Cada campo de `estructura_datos_propiedad_social_fuente.md` tiene entidad/campo, tipo, aplicabilidad, momento de captura y responsable definidos.
- Cada campo aplicable puede capturarse desde UI, llega al backend, se valida, persiste, audita y puede consultarse después.
- Los datos derivados no se duplican y los campos legacy conservan procedencia durante la transición.
- Los valores faltantes y no aplicables son distinguibles; ningún nulo ambiguo fue convertido silenciosamente.

### Cumplimiento del flujo

- Investigación, Negociación y Consolidación están visibles y ejecutables en el orden aprobado.
- La afectación nace al confirmarse los predios/derechos y no como registro prospectivo.
- Las rutas colectiva e individual comparten sólo las etapas comunes y conservan sus diferencias.
- Las decisiones de anuencia, conciliación, acuerdo y expropiación siguen exactamente las conexiones fuente.
- RAN, FIFONAFE, pago y retiro de fondos aplican los gates aprobados, incluidas las ambigüedades resueltas formalmente.

### Integridad y trazabilidad

- PostgreSQL impide las combinaciones y transiciones inválidas que constituyen invariantes estables.
- Backend replica las reglas con mensajes de dominio y autorización por alcance.
- Todas las escrituras y transiciones relevantes son auditables; documentos conservan versiones y hash.
- No hay pérdida de datos, borrados destructivos ni relaciones inferidas sin evidencia.
- Los datos existentes están conciliados, en revisión o bloqueados de forma explícita.

### Experiencia y pruebas

- El usuario comprende Proyecto -> Tramo -> Núcleo -> Expediente -> Afectaciones sin conocer `tramo_nucleo`.
- Cada pantalla indica ubicación, datos faltantes, acciones habilitadas y motivo de bloqueo.
- Existe prueba trazable para cada requisito fuente: unitaria, API, SQL, E2E o UAT según corresponda.
- Pasan las suites de regresión, autorización, aislamiento, PostGIS y los flujos completos colectivo/individual.
- UAT está aprobado sin defectos críticos o altos abiertos.

## 17. Veredicto

`PLAN LISTO CON DECISIONES FUNCIONALES PENDIENTES`

La primera acción no es una migración ni una entidad nueva. Es cerrar D01-D10 y,
en paralelo, preparar la matriz de trazabilidad y el preflight. Una vez cerradas
las decisiones que afectan gates, el primer trabajo de implementación debe
corregir la captura hoy rota o inaccesible: actividades, padrón, RAN,
formularios de convenio por variante y flujo progresivo de FIFONAFE.
