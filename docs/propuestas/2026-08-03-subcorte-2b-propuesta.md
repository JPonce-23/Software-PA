# Propuesta técnica — Subcorte 2B: secuencia, salidas terminales y liberación

**Fecha:** 2026-08-03

**Estado:** propuesta corregida con decisiones funcionales aprobadas; viable para implementación, todavía no implementada

**Alcance:** Corte 2, Subcorte 2B

**Fuente de continuidad:** `ESTADO_PROYECTO.md`
**Fuentes funcionales vigentes:** `docs/Flujo liberacion derechos.md`, `docs/Descripción proceso.md`, `docs/requirements.md` y el flujograma de propiedad social referido por esos documentos.

Esta propuesta se elaboró mediante inspección de documentación, migraciones, esquema activo, backend, frontend y pruebas. No ejecuta migraciones, no modifica la base, no implementa código y no actualiza `ESTADO_PROYECTO.md`.

## 1. Trabajo vigente identificado

El siguiente trabajo vigente es el **Subcorte 2B del Corte 2: secuencia del flujo, salidas terminales y liberación por afectación**. El Subcorte 2A ya está implementado mediante la migración `005_subcorte_2a_integridad_afectaciones.sql` y no debe reimplementarse.

El objetivo de 2B es hacer ejecutables y verificables estas reglas:

1. Respetar la secuencia ordinaria de propiedad social:
   `sensibilización → caminamiento → afectación confirmada → asamblea (sólo colectiva) → convenio → RAN → FIFONAFE → pago → liberación`.
2. Representar por separado el avance operativo, registral, financiero, terminal y de liberación.
3. Determinar la liberación por cada afectación confirmada, y después agregarla al `tramo_nucleo`.
4. Detener el seguimiento ordinario cuando una afectación salga por expropiación directa o comunidad indígena, conservando trazabilidad, notas, documentos y auditoría.
5. Corregir la semántica vigente que equipara indebidamente inscripción en RAN con liberación y clasifica expropiación como problema.

Quedan fuera de 2B:

- la navegación y el aislamiento documental por afectación previstos para 2C;
- propiedad privada, catastro y Registro Público;
- seguimiento de la expropiación o de los procedimientos de comunidad indígena por otras instituciones;
- el ROW versionado del Corte 5;
- avalúos u otros procesos no modelados en las tablas actuales.

## 2. Estado actual verificado

### 2.1 Base activa

La inspección fue exclusivamente de lectura. La base activa verificada fue PostgreSQL 15.4, base `db_trenes`, y contiene las migraciones `004` y `005` registradas en `schema_migrations`.

Datos relevantes observados al 2026-08-03:

| Elemento | Resultado observado |
|---|---:|
| Afectaciones activas colectivas | 2 |
| Afectaciones activas individuales | 4 |
| Afectaciones activas totales | 6 |
| Convenios activos | 2 |
| Trámites FIFONAFE activos | 0 |
| Pagos activos | 0 |
| Actividades de campo realizadas | 0 |
| Afectaciones activas con sensibilización y caminamiento realizados | 0 de 6 |
| Salidas terminales marcadas | 0 |

Por tanto, la base actual contiene datos operativos posteriores a la fotografía descrita en `ESTADO_PROYECTO.md`. No se puede afirmar si son datos reales o de prueba. Tampoco se puede activar una validación histórica estricta sin antes revisarlos: las seis afectaciones activas incumplirían el nuevo antecedente obligatorio de caminamiento.

### 2.2 Esquema y migraciones

Ya está implementado:

- integridad de tipo de afectación, parcela y titular del Subcorte 2A;
- restricciones compuestas relevantes entre tramo, núcleo, afectación y convenio;
- bitácora y contexto de auditoría;
- bajas lógicas mediante `activo`;
- cantidades monetarias con `NUMERIC`, no `float`;
- límite máximo de pago por convenio;
- protección parcial contra regresión de hitos RAN en `convenio`.

No está implementado en PostgreSQL:

- el orden completo del flujo;
- la relación inequívoca de asamblea con afectación;
- la relación de actividades de ciclos adicionales con una afectación concreta;
- la conclusión de “no conflictos” que habilita un pago;
- las salidas terminales por afectación;
- la liberación derivada del pago;
- el agregado correcto de estados mixtos en `tramo_nucleo`;
- autorización territorial.

Las vistas vigentes presentan dos errores funcionales: `vw_tramo_nucleo_estado` deriva liberación a partir de RAN y trata expropiación como problema; las vistas de tablero heredan esa clasificación.

### 2.3 Backend

- Los modelos ORM reflejan en general las tablas actuales, pero no exponen estados 2B ni relaciones directas de asamblea/actividad con una afectación.
- Los contratos de afectación de 2A existen y conservan `Decimal` para dinero.
- Los contratos de actividad, asamblea, convenio y FIFONAFE permiten combinaciones que no respetan la secuencia.
- Los servicios de afectaciones de 2A son transaccionales y auditables, pero no verifican caminamiento ni salidas terminales.
- La lógica de flujo está dispersa entre `app/main.py`, servicios y restricciones SQL; no existe un servicio único de transición.
- El alta de afectación, asamblea, convenio, trámite y pago puede avanzar sin todos sus antecedentes funcionales.
- Algunos manejadores devuelven `str(exc.orig)`, lo que puede exponer detalles internos de PostgreSQL.
- La autenticación y los roles existen, pero `usuario_tramo` no se aplica para restringir lecturas o escrituras por territorio.

### 2.4 Frontend

- `ExpedienteDetail.jsx` organiza el expediente por `tramo_nucleo`, pero no muestra una secuencia verificable por afectación.
- No existe interfaz para capturar sensibilización/caminamiento ni para completar el circuito FIFONAFE/no conflictos.
- Las asambleas se capturan a nivel de `tramo_nucleo`, sin afectación colectiva inequívoca.
- La selección de convenios y asambleas no se limita por ruta, elegibilidad ni contexto.
- `PagosPanel` puede ofrecer pagos sin comprobar desde el backend el cierre registral y de no conflictos.
- El tablero y el mapa consumen la clasificación incorrecta basada en RAN.
- Cálculos monetarios informativos se hacen con `Number`; el frontend no debe tomar decisiones autoritativas de saldo o liberación con esa representación.

### 2.5 Pruebas

- La cobertura existente valida autenticación básica, operaciones CRUD y las reglas del Subcorte 2A.
- Los datos de prueba crean afectaciones sin actividades previas y pagos con convenios que no han concluido el flujo; esas pruebas evidencian la ausencia de 2B y deberán adaptarse.
- No hay cobertura integral de secuencia, terminalidad, estados derivados, agregación mixta, concurrencia de pagos ni pertenencia territorial.
- No se ejecutó la suite durante esta auditoría porque utiliza la base compartida y realiza escrituras/bajas lógicas, contrario a la restricción de esta etapa.

## 3. Reglas funcionales confirmadas

1. El alcance es exclusivamente propiedad social y contempla derechos colectivos e individuales.
2. `tramo_nucleo` representa el expediente territorial maestro; `afectacion` representa el subcaso operativo confirmado.
3. Sensibilización y caminamiento ocurren antes de confirmar una afectación.
4. La ruta colectiva exige asamblea aprobada antes de firmar el convenio.
5. La ruta individual no exige asamblea.
6. Un convenio debe estar firmado antes de ingresar a RAN, e ingresado antes de ser inscrito.
7. La inscripción en RAN es un estado registral intermedio; no equivale a liberación.
8. El flujo FIFONAFE incluye la verificación de no conflictos antes del pago.
9. Una afectación sólo se libera cuando concluye el pago aplicable. Para
   derechos individuales, la evidencia de conclusión es el trámite FIFONAFE
   de indemnización activo con `estatus = 'completo'`. Para derechos
   colectivos se exige, además, una asamblea activa de tipo
   `retiro_fondos`, correspondiente a la misma afectación y ciclo, con
   `estatus_asamblea = 'completo'`.
10. `monto_90` está incluido en `monto_100`; el máximo pagable es `monto_100 + monto_bdt`.
11. Expropiación directa y comunidad indígena son salidas terminales fuera del seguimiento de la PA. No son liberación, problema ni pendiente ordinario.
12. Después de una salida terminal sólo deben conservarse trazabilidad, notas, documentos y auditoría; no debe continuar el flujo ordinario.
13. Los estados se derivan de hechos registrados; no deben ser banderas manuales editables.
14. Un `tramo_nucleo` es liberado únicamente cuando todas sus afectaciones activas ordinarias están liberadas. La coexistencia de rutas liberadas y terminales debe mostrarse como estado mixto.
15. Los convenios modificatorios son revisiones del ciclo principal, mientras que superficie adicional y obras complementarias representan ciclos completos adicionales.
16. No se deben inferir asociaciones históricas ambiguas entre actividades, asambleas, convenios o afectaciones.
17. Los montos de un convenio modificatorio sustituyen definitivamente los
    valores económicos vigentes del convenio padre; no se suman a ellos ni
    crean otra bolsa de pago.
18. En modificatorios colectivos se sustituyen `monto_90`, `monto_100` y
    `monto_bdt`, y el límite vigente es `monto_100 + monto_bdt`. En
    modificatorios individuales se sustituyen `monto_90` y `monto_100`,
    `monto_bdt` no aplica y el límite vigente es `monto_100`.
19. En todos los casos `monto_90` continúa siendo un anticipo incluido en
    `monto_100`; nunca se suma al límite.

## 4. Hallazgos y contradicciones

| ID | Hallazgo | Consecuencia | Clasificación |
|---|---|---|---|
| H-01 | Las vistas actuales consideran liberado al inscribirse en RAN. | Sobreestima superficie liberada y distorsiona tablero/mapa. | Contradicción confirmada |
| H-02 | Expropiación se clasifica como problema. | Confunde una salida de alcance con una incidencia operativa. | Contradicción confirmada |
| H-03 | Las seis afectaciones activas carecen de sensibilización/caminamiento realizados. | Una restricción histórica inmediata bloquearía o invalidaría datos existentes. | Riesgo de compatibilidad |
| H-04 | `asamblea` no identifica la afectación colectiva. | Una asamblea del mismo expediente podría habilitar el convenio equivocado. | Integridad pendiente |
| H-05 | `actividad_campo` no identifica afectación. | Los nuevos ciclos por superficie adicional u obras no se pueden distinguir de forma determinista. | Integridad pendiente |
| H-06 | La relación entre indemnización y dictamen de no conflictos no es explícita. | No se puede probar qué conclusión habilitó un pago. | Integridad pendiente |
| H-07 | Las claves de FIFONAFE son opcionales y `MATCH SIMPLE` admite relaciones parciales. | Se pueden crear trámites sin linaje completo. | Integridad pendiente |
| H-08 | La protección RAN actúa principalmente en actualizaciones y no cubre el flujo completo. | Un alta puede llegar con hitos incoherentes. | Regla parcial |
| H-09 | El tope de pago se evalúa por convenio exacto, no por el ciclo y su versión económica modificada. | Un modificatorio podría fragmentar el control y permitir sobrepago lógico. | Regla resuelta en diseño: sustitución y control por ciclo |
| H-10 | El esquema no deriva “pago concluido” según la ruta. | No se puede derivar liberación con la implementación actual. | Regla resuelta: indemnización completa; en colectivos también retiro de fondos completo |
| H-11 | `usuario_tramo` no filtra consultas ni mutaciones. | Riesgo de IDOR y acceso fuera de la adscripción territorial. | Seguridad pendiente |
| H-12 | El rol geógrafo aparece autorizado en operaciones no geométricas. | La implementación no conserva una separación estricta de responsabilidades. | Contradicción técnica |
| H-13 | Algunos errores SQL se devuelven casi literalmente. | Posible filtración de nombres internos, reglas o fragmentos SQL. | Seguridad pendiente |
| H-14 | El frontend no permite registrar todos los hitos que después tendría que exigir el backend. | Activar reglas estrictas sin interfaz dejaría el proceso inutilizable. | Dependencia de despliegue |
| H-15 | No hay vínculo inequívoco para las ampliaciones individuales. | Los ciclos podrían mezclarse dentro de una afectación. | Resuelto en diseño con `afectacion_ciclo`; no se inventa un reinicio social no documentado |
| H-16 | `ESTADO_PROYECTO.md` describe una base sin datos operativos, pero la base activa ya contiene registros activos. | La continuidad debe actualizarse sólo después de identificar esos datos. | Desfase documental |

## 5. Diseño propuesto

### 5.1 Principio de diseño

Los hechos permanecen en sus tablas operativas y los estados se calculan en vistas/consultas. No se propone un campo manual `estado_liberado`. Las transiciones deben verificarse tanto en el servicio como en PostgreSQL: el servicio produce errores de dominio comprensibles y la base impide que otra ruta de escritura vulnere la integridad.

### 5.2 Unidad de seguimiento

- Unidad maestra: `tramo_nucleo`.
- Unidad de decisión y liberación: `afectacion` activa.
- Unidad de agrupación: ciclo operativo asociado a una afectación. El ciclo
  original se crea junto con la afectación, pero sus actividades previas
  permanecen compartidas en `tramo_nucleo`; los ciclos posteriores se crean
  antes de sus actuaciones exclusivas. Este identificador es técnico y no
  constituye un estado manual.
- Unidad financiera: convenio base y sus revisiones dentro de un ciclo.
- Unidad de revisión: convenio modificatorio enlazado a su convenio/ciclo padre.
- Unidad terminal: afectación. Los indicadores existentes del núcleo o del `tramo_nucleo` podrán actuar como antecedente, pero deben resolverse a un estado efectivo por afectación sin inventar relaciones.

Las actividades de sensibilización y caminamiento del ciclo original deben
permanecer en `tramo_nucleo`, porque ocurren antes de que exista una
`afectacion` y pueden ser antecedentes compartidos. Para superficie adicional
y obras complementarias, que sí abren ciclos después de existir la
afectación, se requiere una identidad de ciclo estable; `contexto_proceso` por
sí solo no distingue dos ciclos del mismo tipo. Se propone una entidad
asociativa `afectacion_ciclo`. El ciclo `cop_original` nace atómicamente al
crear la afectación y los ciclos posteriores son referenciados por sus
actuaciones exclusivas. No se propone agregar un único `id_afectacion`
directamente a toda actividad de campo.

### 5.3 Estados derivados por afectación

Se propone una vista `vw_afectacion_estado` con cinco dimensiones independientes:

| Dimensión | Valores propuestos | Regla general |
|---|---|---|
| `estado_operativo` | `antecedentes_incompletos`, `afectacion_confirmada`, `asamblea_pendiente`, `asamblea_aprobada`, `asamblea_no_aplica` | Derivado de actividades, tipo de afectación y asamblea aplicable. |
| `estado_registral` | `sin_convenio`, `convenio_borrador`, `convenio_firmado`, `ingresado_ran`, `inscrito_ran`, `no_aplica_terminal` | Derivado de hitos de convenio/RAN. |
| `estado_financiero` | `pendiente_fifonafe`, `no_conflictos_pendiente`, `listo_para_pago`, `pago_parcial`, `indemnizacion_completa`, `retiro_fondos_pendiente`, `concluido`, `no_aplica_terminal` | Derivado de trámites, pagos activos y, para colectivos, asamblea de retiro de fondos. `concluido` no depende de alcanzar el máximo económico. |
| `estado_terminal` | `ordinario`, `fuera_seguimiento_expropiacion`, `fuera_seguimiento_comunidad_indigena` | Derivado de la salida terminal efectiva. |
| `estado_liberacion` | `pendiente`, `en_proceso`, `liberada`, `no_aplica_terminal` | `liberada` sólo cuando todos los ciclos pagables aplicables están concluidos. |

La vista debe exponer además indicadores de anomalía, por ejemplo `antecedente_historico_incompleto`, `asociacion_pendiente_revision` y `datos_inconsistentes`. Estos indicadores no sustituyen estados ni autorizan avanzar.

### 5.4 Transiciones permitidas

#### Ruta ordinaria común

1. La sensibilización original puede programarse y realizarse en el
   `tramo_nucleo` y contexto `cop_original`.
2. El caminamiento original puede programarse, pero sólo completarse cuando
   exista sensibilización aplicable realizada en ese expediente y contexto.
3. La afectación puede confirmarse sólo después del caminamiento original
   realizado. Esas actuaciones permanecen como antecedentes compartidos.
4. Si la afectación es colectiva, requiere una asamblea realizada y aprobada ligada a esa afectación.
5. Si la afectación es individual, omite asamblea.
6. El convenio aplicable se firma después del antecedente de su ruta.
7. El ingreso a RAN requiere firma; la inscripción requiere ingreso y fechas cronológicamente válidas.
8. El trámite FIFONAFE aplicable requiere la conclusión registral definida para la ruta.
9. Registrar un pago requiere el informe de no conflictos concluido y
   favorable, y disponibilidad exacta dentro del límite económico vigente del
   ciclo.
10. En una afectación individual, el ciclo financiero queda `concluido`
    cuando su trámite de indemnización activo alcanza `estatus = 'completo'`.
11. En una afectación colectiva, completar la indemnización cambia el estado
    a `retiro_fondos_pendiente`; el ciclo queda `concluido` únicamente cuando
    existe también una asamblea activa de tipo `retiro_fondos`, ligada a la
    misma afectación y ciclo, con `estatus_asamblea = 'completo'` y fecha de
    realización.
12. La afectación se deriva como `liberada` cuando todos sus ciclos base
    activos aplicables están concluidos. El importe máximo no sustituye la
    evidencia de conclusión definida por la ruta.

#### Salidas terminales

Una afectación puede pasar de ruta ordinaria a:

- `fuera_seguimiento_expropiacion`; o
- `fuera_seguimiento_comunidad_indigena`.

Desde ese momento, PostgreSQL y el servicio deben impedir nuevas altas o avances ordinarios de actividad, asamblea, convenio, RAN, FIFONAFE y pago para esa afectación. Deben seguir permitidos lectura, documentos, notas y la bitácora. En 2B la marca terminal no tendrá operación de reversión por API; una eventual corrección queda fuera de este subcorte y requerirá un procedimiento administrativo compensatorio, específico y auditable.

### 5.5 Ciclos y modificatorios

- `cop_original`, `superficie_adicional`, `obras_complementarias`, `ampliacion` y `ampliacion_remanente` son convenios base; `superficie_adicional` y `obras_complementarias` abren expresamente un nuevo ciclo completo de actividades colectivas.
- `ampliacion` y `ampliacion_remanente` registran nueva superficie, montos y seguimiento registral. Como las fuentes no ordenan reiniciar sensibilización/caminamiento para estas variantes individuales, no se inventará ese reinicio: conservan los antecedentes originales de la afectación y continúan con sus hitos expresamente documentados.
- `modificatorio` es una revisión económica de un ciclo base y debe apuntar
  directamente a su convenio base mediante `id_convenio_padre`; no abre un
  nuevo ciclo, no crea un nuevo límite independiente y no se encadena a otro
  modificatorio.
- Al entrar en vigencia, un modificatorio sustituye definitivamente los
  importes económicos del padre para todo el ciclo. Los pagos activos del
  padre y de sus revisiones se acumulan una sola vez contra el límite vigente.
- La vigencia financiera debe ser explícita y temporal. Se proponen
  `vigencia_financiera_desde` y `vigencia_financiera_hasta` para evitar elegir
  silenciosamente por ID o fecha de captura. Sólo puede existir una versión
  financiera vigente por convenio base; activar una nueva revisión cierra la
  anterior dentro de la misma transacción.
- No se puede activar una sustitución cuyo nuevo límite sea menor que la suma
  ya pagada en el ciclo. Los pagos se serializan bloqueando la fila de
  `afectacion_ciclo` correspondiente.
- Para un modificatorio colectivo se requieren `monto_90`, `monto_100` y
  `monto_bdt`; BDT puede ser cero, pero no omitirse. El límite sustituido es
  `monto_100 + monto_bdt`.
- Para un modificatorio individual se requieren `monto_90` y `monto_100`, y
  `monto_bdt` debe permanecer nulo. El límite sustituido es `monto_100`.
- En ambos casos debe cumplirse `0 <= monto_90 <= monto_100`; `monto_90` no se
  agrega al límite.
- El modificatorio continúa el mismo flujo FIFONAFE y de pago del ciclo; no
  crea otra indemnización ni reinicia etapas. La versión económica vigente se
  consulta al validar cada pago.
- La activación financiera exige convenio firmado. En derechos colectivos,
  además exige la inscripción RAN aplicable concluida, porque el modificatorio
  colectivo sí conserva seguimiento registral. En derechos individuales no se
  inventa una nueva inscripción RAN para el modificatorio: la excepción
  funcional documentada mantiene la activación después de la firma y reutiliza
  el flujo registral/FIFONAFE ya vigente del ciclo.
- No se puede activar un modificatorio cuando el ciclo ya está `concluido` o
  la afectación está `liberada`; una corrección económica posterior al cierre
  queda fuera de 2B y requiere un proceso específico.
- La liberación exige que todos los ciclos base activos aplicables estén concluidos.

### 5.6 Agregación a `tramo_nucleo`

Se propone reconstruir `vw_tramo_nucleo_estado` conservando columnas necesarias para compatibilidad y agregando conteos explícitos. `estado_general` debe derivarse así:

| Condición | Estado agregado |
|---|---|
| No existen afectaciones activas | `sin_afectaciones` |
| Hay ruta ordinaria y ninguna ha iniciado avances válidos | `pendiente` |
| Hay alguna ruta ordinaria en avance o pago parcial | `en_proceso` |
| Todas las afectaciones activas son ordinarias y están liberadas | `liberado` |
| Todas son terminales del mismo tipo | salida terminal correspondiente |
| Coexisten liberadas, en proceso o terminales; o hay terminales de distinto tipo | `mixto` |

El tablero debe separar superficie inscrita en RAN, superficie con flujo financiero concluido/liberada y superficie fuera de seguimiento. No se debe renombrar una métrica RAN para aparentar liberación.

## 6. Cambios por capa

Todo cambio propuesto se detalla con problema, solución, justificación, dependencias, riesgo y validación.

### 6.1 PostgreSQL y migraciones

| Archivo/componente | Problema | Solución propuesta | Justificación | Dependencias | Riesgo | Validación |
|---|---|---|---|---|---|---|
| `backend/db/migrations/006_subcorte_2b_secuencia_estados.sql` | No existe entrega versionada para 2B. | Crear una migración transaccional, expansiva, con bloqueo asesor, requisito de `005` y registro de `006` al final. | Reproduce el despliegue y evita estados parciales. | Migración `005`. | Bloqueo breve durante despliegue. | Aplicar sobre copia de base, verificar rollback ante fallo y `schema_migrations`. |
| `afectacion` | No hay salida terminal por subcaso. | Añadir campos nulos `tipo_salida_terminal`, `fecha_salida_terminal` y `motivo_salida_terminal`, con dominio cerrado y consistencia todo-o-nada. | Conserva el caso aun cuando la PA deje de seguirlo. | Decisión de precedencia y corrección. | Conflicto con banderas históricas del padre. | Pruebas SQL de combinaciones válidas/inválidas y bitácora. |
| `afectacion_ciclo` (nueva) | `contexto_proceso` no distingue ciclos repetidos ni proporciona una raíz de bloqueo financiero. | Crear una identidad técnica por afectación y variante, con consecutivo, tipo, superficie base del ciclo, ciclo de vida auditable y sin estado manual. Crear `cop_original` junto con nuevas afectaciones; abrir variantes posteriores explícitamente. La superficie queda como instantánea exacta de la afectación o convenio base aplicable para no duplicarla al cambiar la versión financiera. | Permite enlazar asamblea, convenio, FIFONAFE y pagos, agregar superficie por ciclo y serializar el saldo; sólo actividades posteriores apuntan al ciclo. | Reglas confirmadas para variantes y modificatorios. | Agrega una entidad y requiere transición de datos. | Dos ciclos del mismo tipo no se mezclan; FK compuestas preservan afectación y expediente; la superficie no se duplica por modificatorios; concurrencia bloquea una sola raíz. |
| `asamblea` | No identifica qué afectación/ciclo colectivo autoriza o retira fondos. | Añadir `id_afectacion` y `id_ciclo_afectacion` nulos para compatibilidad, con FK compuestas al mismo `tramo_nucleo`; exigirlos en nuevas asambleas de autorización y retiro de fondos. Para `retiro_fondos`, `completo` exige fecha realizada. | Cumple Requirement 7 y permite derivar el cierre colectivo aprobado sin usar una asamblea ajena. | `afectacion_ciclo`. | Datos históricos sin asociación. | Preflight; rechazo cruzado; indemnización colectiva completa sin retiro sigue no liberada; retiro completo del mismo ciclo concluye. |
| `actividad_campo` | El contexto textual no basta para ciclos posteriores, pero el original precede a la afectación. | Conservar la FK principal a `tramo_nucleo`; añadir sólo `id_ciclo_afectacion` nullable. Debe ser nulo para antecedentes originales compartidos y obligatorio para superficie adicional/obras complementarias. | Respeta Requirements 5 y 6 y la naturaleza compartida del ciclo original sin perder aislamiento posterior. | `afectacion_ciclo`. | Actividades históricas posteriores sin ciclo inequívoco. | Casos originales compartidos, dos ciclos posteriores iguales y rechazo de ciclo de otro expediente. |
| `convenio` | No existe vigencia financiera explícita ni sustitución segura por modificatorio. | Añadir vigencia financiera nula para compatibilidad y restricciones de una sola versión vigente por convenio base. El modificatorio apunta al base, sustituye montos y no puede activarse por debajo de lo pagado. | Ejecuta la decisión aprobada sin sumar montos ni elegir versiones por heurística. | `afectacion_ciclo`. | Modificatorios históricos ambiguos. | Preflight, activación atómica, sustituciones sucesivas, reducción inválida y reglas diferenciadas colectivo/individual. |
| `tramite_fifonafe` | No se conoce qué no-conflicto habilita una indemnización ni qué ciclo concluye. | Añadir vínculo explícito desde la indemnización al trámite de no conflictos y a `afectacion_ciclo`; reforzar linaje y permitir una sola indemnización activa por ciclo. `estatus='completo'` será la evidencia de indemnización concluida. | Hace auditables el antecedente del pago y el cierre individual/colectivo, sin duplicar el flujo por modificatorio. | Modelo FIFONAFE actual y `afectacion_ciclo`. | Requiere adaptar API/UI y revisar trámites históricos. | Pruebas de tipo, unicidad, mismo ciclo, conclusión sin conflictos, referencias cruzadas y transición a completo. |
| Funciones/triggers 2B | Las escrituras directas pueden omitir la secuencia. | Crear funciones de validación de transición para actividades, afectaciones, asambleas, convenios, FIFONAFE, pagos y terminalidad. Cubrir `INSERT`, reactivación y cambios de hitos. | La integridad crítica no puede depender sólo de FastAPI. | Nuevos vínculos y decisiones funcionales. | Bloqueos o falsos positivos si la transición está mal definida. | Matriz SQL positiva/negativa y concurrencia. |
| Control de pagos | El tope actual opera por trámite/convenio exacto. | Bloquear `afectacion_ciclo`, sumar una sola vez todos los pagos activos de su convenio base y modificatorios, y comparar con la versión financiera vigente: colectivo `monto_100 + monto_bdt`; individual `monto_100`. | Ejecuta la sustitución definitiva, evita bolsas duplicadas y condiciones de carrera. | Ciclo y vigencia financiera. | Consultas o asociaciones de linaje incorrectas producirían saldo falso. | Pagos concurrentes, dos modificatorios sucesivos, pagos previos, reducción de límite y centavos exactos. |
| `vw_afectacion_estado` | No hay estado multidimensional por afectación. | Crear vista derivada con estados, importes, elegibilidad y anomalías. Individual concluye con indemnización completa; colectivo exige además retiro de fondos completo por cada ciclo. | Separa hechos de presentación y ejecuta la evidencia de cierre aprobada sin bandera manual. | Toda la secuencia. | Complejidad/rendimiento. | Datos patrón para cada estado/ruta, múltiples ciclos y `EXPLAIN`. |
| `vw_tramo_nucleo_estado` | RAN se interpreta como liberación y terminal como problema. | Reemplazar lógica conservando compatibilidad de columnas y añadiendo conteos/estado general correcto. | Corrige semántica sin romper consumidores de golpe. | Vista por afectación. | Cambios visibles en tablero. | Comparación antes/después con casos ordinarios, terminales y mixtos. |
| Vistas de tablero/mapa | Métricas heredadas son incorrectas. | Separar métricas registrales, financieras, liberadas y terminales. | Evita decisiones basadas en datos mal etiquetados. | Nuevas vistas. | Diferencias con reportes anteriores. | Totales conciliados contra consultas de detalle. |

### 6.2 ORM y contratos

| Archivo/componente | Problema | Solución propuesta | Justificación | Dependencias | Riesgo | Validación |
|---|---|---|---|---|---|---|
| `backend/app/models.py` | Faltan campos y relaciones 2B. | Mapear los campos terminales y nuevos vínculos; declarar relaciones de sólo lectura hacia vistas cuando resulte útil. | Mantiene ORM alineado con 006. | Migración 006. | Ciclos ORM o cargas innecesarias. | Importación de modelos y consultas controladas. |
| `backend/app/schemas.py` | Contratos admiten hitos incoherentes, no expresan vigencia financiera ni cierre por ruta. | Crear contratos específicos para completar indemnización, completar retiro de fondos y activar modificatorio; enums/Literal cerrados, DTO de estado/elegibilidad y `Decimal` para dinero. Colectivo modificatorio exige BDT; individual lo prohíbe. | Evita usar CRUD genérico como máquina de estados y hace explícitas las decisiones aprobadas. | Servicio de flujo. | Ruptura de clientes si se reemplaza de una vez. | OpenAPI, matrices Pydantic por ruta y pruebas de compatibilidad. |
| Contrato de salida terminal | No existe operación explícita y auditable. | Añadir solicitud con tipo, motivo obligatorio y confirmación; respuesta con estado efectivo. | Una salida irreversible no debe ser un parche genérico. | Decisión sobre corrección. | Marcación accidental. | Pruebas de rol, territorio, repetición e intento de avance posterior. |
| Contratos monetarios | El navegador convierte valores a `Number`. | Publicar importes como decimales serializados y saldos calculados por backend. | Preserva precisión y autoridad del servidor. | Estado financiero. | Ajustes de formato en UI. | Casos con centavos y montos grandes. |

### 6.3 Servicios, endpoints y manejo de errores

| Archivo/componente | Problema | Solución propuesta | Justificación | Dependencias | Riesgo | Validación |
|---|---|---|---|---|---|---|
| `backend/app/services/flujo.py` (nuevo) | Reglas dispersas en rutas y SQL. | Centralizar precondiciones, transiciones, sustitución financiera, cierre por ruta y estados; bloquear la raíz del ciclo y usar una transacción por operación. | Reduce divergencia y mantiene saldo/liberación atómicos. | Repositorios/modelos 2B. | Duplicación temporal durante transición. | Pruebas unitarias, concurrencia y rollback total. |
| `backend/app/services/access.py` (nuevo) | No se aplica pertenencia territorial. | Resolver `id_tramo` desde cada recurso y exigir `usuario_tramo.activo`; administrador conserva acceso global. | Previene IDOR y cumple autorización territorial. | Modelo `usuario_tramo`. | Usuarios actuales sin asignación. | Matriz rol × territorio × operación. |
| Rutas de actividades/afectaciones/asambleas/convenios/FIFONAFE/pagos | CRUD permite saltos del flujo. | Mantener URLs compatibles cuando sea posible, pero delegar mutaciones al servicio 2B y devolver `409` con código de dominio al incumplir una transición. | Migración incremental sin duplicar negocio. | Servicio de flujo. | Clientes dependientes de respuestas anteriores. | Contratos API y regresión de rutas. |
| `GET/POST /api/afectaciones/{id}/ciclos` | El diseño identifica ciclos posteriores, pero no define cómo abrirlos antes de capturar sus actividades. | Listar los ciclos de la afectación y crear explícitamente `superficie_adicional`, `obras_complementarias`, `ampliacion` o `ampliacion_remanente`; `cop_original` se crea de forma atómica con la afectación y no se admite por esta operación. | Evita crear ciclos implícitos desde un convenio y proporciona una raíz estable para actividades, asambleas, convenios, FIFONAFE y bloqueo financiero. | Servicio de flujo, autorización territorial y contratos de ciclo. | Duplicados o apertura de una variante incompatible con el tipo de derecho. | Rol/territorio, matriz derecho × tipo de ciclo, consecutivos, idempotencia y dos ciclos repetidos sin mezcla. |
| `GET /api/afectaciones/{id}/estado` | El cliente reconstruiría reglas. | Exponer estado derivado, antecedentes, acciones permitidas y motivos de bloqueo. | El backend queda como autoridad. | Vista 2B. | Consultas N+1. | Pruebas de respuesta para todos los estados. |
| `GET /api/tramos-nucleos/{id}/estado` | No hay agregado correcto. | Exponer estado general y resumen por afectación. | Habilita expediente, tablero y mapa coherentes. | Vistas 2B. | Respuesta pesada. | Perfil de consulta y paginación/detalle. |
| `POST /api/fifonafe/{id}/completar-indemnizacion` y `POST /api/asambleas/{id}/completar-retiro-fondos` | Un `PUT` genérico podría declarar cierre sin validar la ruta. | Añadir operaciones específicas; el servicio valida RAN, no conflictos, afectación/ciclo, rol y territorio antes de cambiar el hito. | El cierre que deriva liberación requiere intención explícita y auditoría. | Servicio de flujo y contratos. | Reintentos o cierre del ciclo equivocado. | Idempotencia, referencias cruzadas, individual/colectivo y bitácora. |
| `POST /api/convenios/{id}/activar-modificatorio` | Un alta genérica no puede sustituir montos y cerrar vigencias atómicamente. | Añadir transición que bloquea el ciclo, valida montos, pagos acumulados y vigencia, cierra la versión anterior y activa la sustitución en una sola transacción. | Previene ventanas de doble versión y sobrepago. | Vigencia financiera y servicio de flujo. | Contención concurrente por ciclo. | Dos activaciones concurrentes, reducción bajo lo pagado, intento posterior al cierre y rollback. |
| `PUT /api/afectaciones/{id}/salida-terminal` | No hay transición terminal explícita. | Implementar transición protegida, idempotente sólo para el mismo hecho y auditada. | Evita edición silenciosa. | Contrato terminal. | Reversibilidad no definida. | Auditoría, repetición, conflicto de tipo y bloqueo posterior. |
| Manejo global de excepciones | Se expone `exc.orig`. | Traducir restricciones conocidas a códigos seguros y registrar el detalle sólo en logs internos; usar mensaje genérico para fallos inesperados. | No expone esquema ni datos internos. | Catálogo de errores 2B. | Perder diagnóstico si el log es insuficiente. | Pruebas que aseguren ausencia de SQL/secretos en respuesta. |
| Auditoría | Las nuevas operaciones podrían omitir contexto. | Hacer obligatorio `set_audit_context` dentro del límite transaccional de toda escritura 2B. | Conserva el mecanismo vigente. | Sesión DB y usuario autenticado. | Evento sin actor ante rutas auxiliares. | Consultar bitácora tras cada transición de prueba. |

### 6.4 Frontend

| Archivo/componente | Problema | Solución propuesta | Justificación | Dependencias | Riesgo | Validación |
|---|---|---|---|---|---|---|
| `frontend/src/pages/ExpedienteDetail.jsx` | No muestra secuencia por afectación. | Añadir resumen 2B con estados independientes, siguiente acción permitida y bloqueos. Conservar navegación maestra; el aislamiento completo sigue en 2C. | Hace visible el estado real sin invadir el siguiente subcorte. | Endpoints de estado. | Sobrecarga visual. | Pruebas de render para rutas colectiva, individual, terminal y mixta. |
| Captura de actividades | No existe UI para sensibilización/caminamiento. | Incorporar panel mínimo para programar/completar actividades aplicables con fechas y contexto. | Sin este panel no puede cumplirse la secuencia. | API de actividades validada. | Introducir ciclos ambiguos. | Flujo feliz y bloqueo de caminamiento prematuro. |
| `FormAsamblea` | Opera a nivel maestro y no filtra afectación. | Iniciarlo desde una afectación colectiva elegible y fijar su referencia/contexto. | Evita asociación accidental. | `asamblea.id_afectacion`. | Asambleas históricas sin vínculo. | No ofrecer individuales ni colectivas no elegibles. |
| `FormConvenio` | Ofrece variantes y asambleas no elegibles; no administra RAN ni sustitución financiera como transiciones. | Separar creación, firma, ingreso e inscripción; filtrar variante/asamblea. Para modificatorio mostrar importes vigentes del padre, capturar los valores sustitutos completos y su vigencia, y confirmar la activación sin sumar visualmente ambos convenios. | Cada botón representa una transición auditable y evita interpretar el modificatorio como incremento. | Servicio 2B y endpoint de activación. | Más pasos de interacción o confusión entre valor anterior/nuevo. | E2E de transiciones, colectivo/individual, vista previa de saldo y errores 409. |
| Panel FIFONAFE | No existe circuito completo ni cierre diferenciado por ruta. | Añadir captura/consulta de no conflictos e indemnización enlazados al ciclo. Al completar indemnización, la ruta individual puede concluir y la colectiva debe mostrar `retiro_fondos_pendiente`. | Materializa la evidencia de cierre aprobada. | Relaciones FIFONAFE y estados 2B. | Interpretar de forma errónea estados históricos. | Casos con conflicto, individual completo y colectivo aún sin retiro. |
| Panel de asambleas colectivas | No existe una acción inequívoca de retiro de fondos por ciclo. | Permitir crear/completar `retiro_fondos` sólo desde una afectación colectiva con indemnización completa y fijar afectación/ciclo. | Evita usar una asamblea de otro expediente para liberar. | Asociación de asamblea y servicio de flujo. | Duplicidad o cierre accidental. | Sólo una conclusión aplicable por ciclo, idempotencia y autorización. |
| `PagosPanel` | Permite intentar pagos prematuros y calcula autoridad con `Number`. | Mostrar pago sólo si `puede_pagar` viene del backend; enviar cadena decimal y usar saldo/versión económica retornados por API. No inferir conclusión por suma ni por `tipo_pago`. | Evita imprecisión, saltos de flujo y confusión entre límite y cierre. | Estado financiero y servicio pagos. | Diferencias de formato. | Centavos, pago parcial, sustitución vigente y sobrepago concurrente. |
| Dashboard, lista y mapa | Presentan RAN como liberación. | Consumir estados/métricas corregidos y mostrar registral, liberado, terminal y mixto por separado. | Alinea toda la UI con la fuente funcional. | Vistas/API 2B. | Cambio de cifras frente a reportes previos. | Conciliación contra detalle de afectaciones. |

### 6.5 Pruebas y documentación

| Archivo/componente | Problema | Solución propuesta | Justificación | Dependencias | Riesgo | Validación |
|---|---|---|---|---|---|---|
| Fixtures backend | Crean datos saltando la secuencia. | Crear fábricas de flujo válidas y fábricas deliberadamente inválidas; aislar la base de prueba. | La prueba debe representar el dominio vigente. | Migración 006. | Migración extensa de pruebas. | Suite reproducible desde base vacía. |
| Pruebas SQL/API | No cubren 2B ni concurrencia. | Añadir matriz de transición, terminalidad, estados, permisos, auditoría y carreras de pago. | Las reglas críticas necesitan defensa en profundidad. | Todos los componentes 2B. | Falsos positivos por estado compartido. | Ejecución aislada y repetible. |
| Pruebas frontend | No hay cobertura funcional del flujo. | Añadir pruebas de componentes/flujo y mantener lint/build. | Evita volver a ofrecer acciones prohibidas. | Contratos estables. | Nueva infraestructura de pruebas. | Ejecución en CI con API simulada por contrato. |
| Documentación OpenAPI y funcional | Los clientes no conocen estados ni errores. | Documentar transiciones, códigos 409, permisos y precisión monetaria. | Facilita adopción incremental. | Contratos finales. | Desalineación posterior. | Revisión cruzada con OpenAPI generado. |

## 7. Migración y compatibilidad

### 7.1 Estrategia expansiva

La migración 006 deberá:

1. Ejecutarse en una sola transacción y tomar un bloqueo asesor.
2. Comprobar que `005` está aplicada.
3. Crear columnas nuevas como nulas para conservar registros existentes.
4. Crear claves, checks, índices, funciones y triggers sin borrar datos.
5. Conservar las interfaces de vistas necesarias mientras se corrige su semántica y se agregan columnas.
6. Registrar `006` sólo al final.
7. Fallar completa y limpiamente si no puede instalar todos los objetos.

Objetos expansivos mínimos previstos:

- tabla `afectacion_ciclo`, con FK compuestas a afectación y
  `tramo_nucleo`, consecutivo por afectación y claves candidatas para que las
  demás relaciones no puedan cruzar expedientes;
- `convenio.id_ciclo_afectacion`, además de
  `vigencia_financiera_desde`/`vigencia_financiera_hasta` para
  modificatorios;
- `actividad_campo.id_ciclo_afectacion` nullable sólo para ciclos posteriores;
- `asamblea.id_afectacion` e `id_ciclo_afectacion`, obligatorios en nuevas
  asambleas de autorización y retiro de fondos;
- `tramite_fifonafe.id_ciclo_afectacion` y
  `id_tramite_no_conflictos`, con unicidad parcial de indemnización activa por
  ciclo;
- campos terminales en `afectacion` y checks de consistencia;
- índices parciales para una sola versión financiera abierta por convenio
  base y una sola indemnización activa por ciclo;
- triggers de secuencia, vigencia, cierre por ruta, saldo concurrente y
  terminalidad, además de las vistas derivadas corregidas.

No se propone asignar automáticamente ciclos o afectaciones a actividades o
asambleas históricas. Coincidir por `tramo_nucleo`, fecha o tipo no demuestra
identidad. Las actividades originales continúan como antecedentes compartidos
del expediente maestro y no requieren una asociación artificial.

### 7.2 Preflight obligatorio

Antes de aplicar 006 en cada ambiente se debe generar, sin modificar datos:

- versión de migración y firma de objetos relevantes;
- afectaciones activas sin sensibilización/caminamiento;
- asambleas sin asociación inequívoca;
- convenios con hitos incompletos o cronología inválida;
- modificatorios sin padre base inequívoco, con importes incompatibles o con
  más de una posible versión financiera vigente;
- trámites FIFONAFE con referencias parciales;
- indemnizaciones completas sin ciclo inequívoco y, en colectivos, sin
  asamblea de retiro de fondos completa del mismo ciclo;
- pagos que no puedan asociarse a un ciclo válido;
- ciclos cuyo total pagado excedería el límite sustituido por un
  modificatorio;
- combinaciones de marcas terminales en núcleo, expediente y afectación;
- usuarios no administradores sin asignación territorial activa.

El resultado debe conservar identificadores, no datos personales innecesarios.

### 7.3 Convivencia con datos actuales

Los seis registros activos observados no deben borrarse, desactivarse ni completarse con eventos ficticios. La migración puede instalar reglas para nuevas altas y avances, mientras las vistas marcan los casos históricos como `antecedentes_incompletos`. Posteriormente, una revisión autorizada decidirá si existe evidencia para registrar hechos históricos reales.

Las columnas de ciclo y vigencia financiera se agregan nulas. La migración
creará una fila estructural `cop_original` por afectación existente porque esa
unidad está confirmada por el modelo, pero no le asociará automáticamente
actividades, asambleas, convenios o trámites ambiguos. No se elegirá
automáticamente un modificatorio histórico vigente ni se marcará una
indemnización/asamblea como completa. Los modificatorios nuevos deberán usar
la transición de activación; los históricos quedarán señalados para revisión
hasta que su vigencia pueda sustentarse. En la base local observada no existen
pagos ni trámites FIFONAFE activos, pero la migración debe ser segura también
en otros ambientes y abortar antes de cambiar el esquema si detecta un
sobrepago bajo la versión que se pretenda activar.

Las restricciones que dependan de asociaciones históricas podrán instalarse como `NOT VALID` cuando PostgreSQL lo permita: se aplicarán a datos nuevos, y se validarán tras la conciliación. Los triggers deben activarse sólo sobre la transición relevante para evitar que una corrección no relacionada quede bloqueada por un antecedente histórico.

### 7.4 Orden de despliegue

1. Respaldo y preflight; detener temporalmente escrituras y obtener un reporte
   de ciclos, modificatorios, indemnizaciones completas y retiros de fondos.
2. Aplicar migración expansiva 006 en una copia y después en el ambiente objetivo.
3. Desplegar backend compatible con columnas nulas y nuevas respuestas.
4. Desplegar frontend que capture todos los antecedentes antes de endurecer la experiencia.
5. Conciliar manualmente datos históricos sin inferencias.
6. Validar restricciones pendientes y habilitar reglas estrictas restantes.
7. Conciliar tablero y reportes contra consultas de detalle.

El rollback operativo preferido es restaurar el respaldo o corregir mediante una migración posterior. No se propone una migración destructiva inversa que elimine evidencia capturada.

## 8. Seguridad, autorización e integridad

### 8.1 Autorización

- Administrador: acceso global y transiciones administrativas.
- Operador: lecturas y escrituras de negocio sólo en tramos asignados activamente.
- Geógrafo: lecturas asignadas y escrituras exclusivamente geométricas autorizadas; no debe firmar convenios, concluir trámites ni registrar pagos.
- Visualizador: sólo lectura de tramos asignados.

La pertenencia territorial debe comprobarse al listar y al operar sobre IDs concretos. No basta con ocultar filas en el frontend. La resolución debe recorrer de forma segura el recurso hacia `tramo` y devolver `404` o una respuesta autorizativa uniforme que no permita enumerar recursos ajenos.

### 8.2 Integridad transaccional

- Toda operación compuesta se ejecuta en una sola transacción.
- PostgreSQL repite las invariantes críticas mediante constraints/triggers.
- Los pagos bloquean la raíz del ciclo para serializar la comprobación del saldo.
- Las fechas se comparan como `TIMESTAMPTZ` y no pueden retroceder hitos concluidos.
- Los importes se mantienen en `NUMERIC`/`Decimal`; el cliente sólo presenta valores.
- No hay bajas físicas de entidades operativas.
- Una salida terminal bloquea el avance incluso si se intenta escribir directamente en la base.

### 8.3 Auditoría y confidencialidad

- Cada escritura 2B debe establecer usuario, motivo y contexto mediante el mecanismo de auditoría existente.
- El evento terminal debe registrar tipo, motivo, fecha y actor.
- No se deben incluir secretos, SQL, nombres internos o valores sensibles en respuestas de error.
- Los logs internos deben usar identificadores de correlación y evitar registrar documentos o datos personales completos.
- Las correcciones administrativas deben quedar como nuevos eventos auditables; no se debe reescribir silenciosamente la historia.

## 9. Plan incremental de implementación

### Fase 0 — Decisiones incorporadas y línea base

- Crear base de pruebas aislada y capturar preflight de los datos actuales.
- Convertir las decisiones aprobadas de cierre por ruta y sustitución
  económica en casos de prueba antes de escribir la migración.
- Congelar el contrato de estados y errores.

**Salida:** reglas aprobadas reproducidas como casos de prueba y ningún dato
ambiguo inferido.

### Fase 1 — Migración expansiva

- Implementar 006 con columnas, relaciones, índices y vistas.
- Instalar validaciones de nuevas transiciones y control concurrente de pagos.
- Mantener datos históricos y exponer anomalías.

**Salida:** esquema capaz de representar 2B y resistente a escrituras directas inválidas.

### Fase 2 — Dominio backend

- Mapear ORM y contratos.
- Implementar servicio de flujo y acceso territorial.
- Adaptar rutas existentes y añadir consultas de estado/salida terminal.
- Sanear errores y verificar auditoría.

**Salida:** API transaccional y autoritativa.

### Fase 3 — Experiencia frontend mínima 2B

- Capturar sensibilización/caminamiento.
- Mostrar estados y acciones permitidas por afectación.
- Adaptar asamblea, convenio, RAN, FIFONAFE y pagos.
- Corregir tablero, lista y mapa.

**Salida:** todos los antecedentes exigidos pueden registrarse sin invadir 2C.

### Fase 4 — Conciliación y endurecimiento

- Revisar las seis afectaciones activas y asociaciones históricas.
- Registrar sólo hechos sustentados documentalmente.
- Validar constraints diferidas.
- Conciliar métricas y retirar rutas internas que omitan el servicio.

**Salida:** reglas estrictas y deuda histórica identificada.

### Fase 5 — Validación y cierre

- Ejecutar matriz completa en base aislada.
- Ensayar despliegue y restauración.
- Validar aceptación funcional con casos colectivos, individuales, terminales y mixtos.
- Sólo entonces actualizar `ESTADO_PROYECTO.md`.

## 10. Matriz de pruebas

| Nivel | Caso | Resultado esperado |
|---|---|---|
| DB | Completar caminamiento sin sensibilización realizada | Rechazo atómico. |
| DB/API | Crear o reactivar afectación sin caminamiento concluido | Rechazo con código de dominio seguro. |
| DB/API | Crear asamblea para afectación individual o de otro expediente | Rechazo. |
| DB/API | Firmar convenio colectivo sin asamblea aprobada aplicable | Rechazo. |
| DB/API | Firmar convenio individual sin asamblea | Permitido si los antecedentes comunes están completos. |
| DB/API | Registrar ingreso RAN sin firma o inscripción sin ingreso | Rechazo. |
| DB/API | Retroceder un hito registral concluido | Rechazo y auditoría sin cambio parcial. |
| DB/API | Crear FIFONAFE antes de la conclusión registral aplicable | Rechazo. |
| DB/API | Pagar sin dictamen de no conflictos o con conflictos | Rechazo. |
| DB | Dos pagos concurrentes que juntos exceden el saldo | Sólo uno puede confirmar; nunca hay sobrepago. |
| DB/API | Individual con indemnización pendiente y pagos registrados | No se libera; el importe pagado no presume conclusión. |
| DB/API | Individual con indemnización completa | Su ciclo queda `concluido`; la afectación se libera sólo si todos sus ciclos aplicables concluyeron. |
| DB/API | Colectivo con indemnización completa y sin retiro de fondos completo | Estado `retiro_fondos_pendiente`; no se libera. |
| DB/API | Colectivo con indemnización y retiro de fondos completos en el mismo ciclo | Su ciclo queda `concluido`; puede derivar liberación si no quedan otros ciclos pendientes. |
| DB/API | Retiro de fondos completo de otra afectación o ciclo | Rechazo y ninguna liberación. |
| DB/API | `monto_90` se intenta sumar adicionalmente | El máximo sigue siendo `monto_100 + monto_bdt`. |
| DB/API | Modificatorio colectivo vigente | Sustituye 90/100/BDT; límite del ciclo = nuevo 100 + nuevo BDT, sin sumar padre. |
| DB/API | Modificatorio individual con BDT | Rechazo; sólo sustituye 90/100 y el límite es el nuevo 100. |
| DB/API | Activar modificatorio colectivo firmado pero sin inscripción RAN aplicable | Rechazo; no cambia la versión financiera vigente. |
| DB/API | Activar modificatorio individual firmado sin una nueva inscripción RAN propia | Permitido si el ciclo ya cumple sus antecedentes aplicables; no se inventa un segundo trámite RAN. |
| DB/API | Segundo modificatorio del mismo convenio base | Cierra la vigencia anterior y sustituye valores en una sola transacción. |
| DB/API | Modificatorio cuyo límite queda bajo pagos acumulados | Rechazo atómico; la versión previa conserva vigencia. |
| DB | Pago concurrente con activación de modificatorio | Ambos serializan por ciclo y el resultado nunca excede el límite finalmente vigente. |
| DB/API | Marcar salida terminal y después intentar avanzar | Marca auditada; todo avance ordinario se rechaza. |
| DB/API | Abrir un ciclo posterior compatible y capturar sus actividades | El ciclo se crea explícitamente, conserva consecutivo único y todas sus etapas quedan aisladas de otros ciclos. |
| DB/API | Intentar abrir `cop_original` manualmente o un ciclo colectivo para una afectación individual | Rechazo sin crear filas parciales. |
| DB/API | Consultar estado terminal | `no_aplica_terminal`, nunca `liberada` ni `problema`. |
| Vista | Afectación inscrita en RAN sin pago | Registral `inscrito_ran`, liberación no concluida. |
| Vista | Todos los ciclos ordinarios concluidos según su ruta | `tramo_nucleo.estado_general = liberado`. |
| Vista | Una liberada y una terminal | Estado general `mixto`, con conteos correctos. |
| Compatibilidad | Se instala 006 con los seis casos históricos incompletos | No se inventan antecedentes; aparecen como anomalías revisables. |
| Autorización | Operador asignado actúa en su tramo | Permitido según rol. |
| Autorización | Operador usa ID de tramo no asignado | Denegado sin filtrar existencia sensible. |
| Autorización | Geógrafo intenta registrar pago o firmar convenio | Denegado. |
| Autorización | Visualizador intenta cualquier escritura | Denegado. |
| Auditoría | Cada transición exitosa y fallida relevante | Escritura exitosa tiene actor/contexto; un fallo no deja cambios parciales. |
| Seguridad | Violación SQL y error inesperado | Respuesta sin SQL, esquema, credenciales ni traza interna. |
| Frontend | Acción no elegible | No se ofrece; si se fuerza, API la rechaza. |
| Frontend | Importe con centavos | Se conserva exactamente como cadena/decimal y saldo del backend. |
| Regresión | Casos de integridad de 2A | Continúan pasando sin relajación. |
| Despliegue | Fallo a mitad de 006 | Transacción revierte y no registra versión 006. |

## 11. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Asociar automáticamente datos históricos equivocados | Corrupción semántica y liberaciones falsas | No inferir; preflight y conciliación manual con evidencia. |
| Activar reglas antes de disponer de UI | Bloqueo operativo | Despliegue por fases y frontend mínimo antes del endurecimiento final. |
| Sobrepago por concurrencia o modificatorios | Impacto financiero crítico | Bloqueo de la fila `afectacion_ciclo`, suma única del linaje, `NUMERIC` y control duplicado en PostgreSQL/servicio. |
| Confundir RAN con liberación en consumidores antiguos | Reportes incorrectos | Compatibilidad de columnas, métricas separadas y conciliación antes de publicar. |
| Modificatorios históricos sin vigencia explícita | Saldo o versión económica incorrectos | No inferir versión; preflight y conciliación documentada antes de habilitarlos. |
| Indemnización histórica completa sin retiro colectivo asociado | Liberación colectiva falsa o bloqueada | No asociar por fecha/expediente; exigir vínculo de afectación/ciclo y revisión manual. |
| Banderas terminales contradictorias entre niveles | Estados no deterministas | No aplicar precedencia; bloquear avance, exponer anomalía y exigir corrección de origen. |
| Reversión terminal sin control | Reapertura silenciosa de un caso fuera de alcance | No ofrecer reversión por API en 2B; una futura corrección deberá ser compensatoria y auditable. |
| Consultas de vistas demasiado costosas | Lentitud en expediente/tablero | Índices por claves activas/ciclo, `EXPLAIN ANALYZE` en copia y paginación. |
| Introducir autorización territorial rompe usuarios actuales | Interrupción de acceso | Preflight de asignaciones, corrección administrativa previa y pruebas por rol. |
| Suite contra base compartida | Residuos e interferencia con datos | Base aislada efímera para pruebas y limpieza transaccional. |
| Errores internos expuestos | Fuga de implementación o datos | Catálogo de errores seguro y detalle sólo en logs internos. |

## 12. Criterios de aceptación

El Subcorte 2B podrá considerarse terminado sólo cuando:

1. La migración 006 se aplique de forma atómica sobre una copia representativa con 004 y 005.
2. Ningún dato histórico haya sido eliminado o asociado por inferencia.
3. La base y la API impidan saltar la secuencia confirmada.
4. La ruta colectiva exija su asamblea aprobada y la individual no la exija.
5. RAN se muestre como estado registral y nunca baste para liberar.
6. Un pago sólo pueda registrarse después del cierre aplicable de RAN y del informe de no conflictos concluido y favorable.
7. Para derechos individuales, cada ciclo concluya únicamente con su indemnización activa en `completo`; para colectivos, exija además retiro de fondos completo del mismo ciclo.
8. Alcanzar el máximo o capturar un pago `total` no libere por sí mismo una afectación.
9. Un modificatorio sustituya definitivamente los importes de su convenio base sin sumarlos, conserve una sola vigencia y acumule los pagos del ciclo una sola vez.
10. El límite vigente de un modificatorio colectivo sea nuevo `monto_100 + monto_bdt`; el individual prohíba BDT y use nuevo `monto_100`; en ambos, `monto_90` esté incluido en `monto_100`.
11. Ninguna sustitución pueda reducir el límite por debajo de pagos acumulados y pagos/activaciones concurrentes queden serializados por ciclo.
12. Todo ciclo posterior se abra mediante una operación explícita, compatible con el tipo de derecho y autorizada por territorio; `cop_original` nazca atómicamente con la afectación.
13. La activación de un modificatorio exija firma; el colectivo exija además su inscripción RAN aplicable y el individual no invente una inscripción propia adicional.
14. La liberación por afectación se derive de la conclusión de todos sus ciclos pagables aplicables.
15. El agregado de `tramo_nucleo` distinga pendiente, en proceso, liberado, terminal y mixto.
16. Expropiación directa y comunidad indígena detengan el flujo y permanezcan fuera de seguimiento, sin aparecer como liberación o problema.
17. Todas las escrituras de 2B respeten rol, pertenencia territorial y auditoría.
18. Ningún endpoint exponga errores internos o secretos.
19. El frontend permita capturar los antecedentes exigidos y sólo ofrezca acciones habilitadas por el backend.
20. Los importes se transmitan y validen sin `float`/`Number` autoritativo.
21. Las pruebas de 2B, seguridad, concurrencia y regresión 2A pasen en una base aislada.
22. Tablero, mapa, listas y detalle concilien sus cifras con la misma definición de estado.
23. Las anomalías de los registros existentes estén identificadas y resueltas o aceptadas explícitamente antes de validar constraints históricas.

## 13. Actualizaciones previstas para `ESTADO_PROYECTO.md`

`ESTADO_PROYECTO.md` no se modifica en esta etapa. Después de una implementación validada deberán actualizarse:

- **Encabezado y fecha de corte:** fecha real de validación, rama y commit.
- **Estado de la base activa:** migración `006`, ambiente validado y resultado del preflight/conciliación.
- **Trabajo terminado:** reglas, vistas, endpoints, UI y pruebas efectivamente entregados; no los propuestos.
- **Corte 2 / Subcorte 2B:** marcarlo completo sólo si cumple todos los criterios de aceptación.
- **Reglas obligatorias:** incorporar el contrato final de estados, terminalidad, ciclos y pago concluido.
- **Archivos y rutas relevantes:** migración, servicios, contratos, vistas, componentes y pruebas realmente creados.
- **Limitaciones y deuda conocida:** asociaciones históricas pendientes, constraints no validadas o decisiones aplazadas.
- **Evidencia de validación:** comandos, conteos y resultados reproducibles sin secretos.
- **Siguiente trabajo vigente:** pasar a 2C únicamente después del cierre formal de 2B.

No debe copiarse esta propuesta como si fuera estado implementado; sólo deben documentarse decisiones aprobadas y comportamiento comprobado.

## 14. Decisiones incorporadas y resultado de gates

### 14.1 Decisiones funcionales incorporadas

| ID | Estado | Regla incorporada | Consecuencia ejecutable |
|---|---|---|---|
| D-01 | Aprobada por el usuario el 2026-08-03 | Individual: indemnización `completo`. Colectivo: indemnización `completo` más asamblea `retiro_fondos` `completo` del mismo ciclo. | Define `estado_financiero = concluido` y permite derivar liberación; ni el máximo ni `tipo_pago='total'` bastan por sí solos. |
| D-04 | Aprobada por el usuario el 2026-08-03 | El modificatorio sustituye definitivamente los importes del convenio base; no los suma. Colectivo sustituye 90/100/BDT y usa límite 100+BDT; individual sustituye 90/100, prohíbe BDT y usa límite 100. | Una sola versión financiera vigente por ciclo, pagos acumulados del linaje y rechazo si el nuevo límite queda bajo lo pagado. |

### 14.2 Controles de diseño cerrados

- `afectacion_ciclo` se adopta como identidad técnica necesaria para ciclos
  repetibles y como raíz de serialización; no agrega lógica funcional ni un
  estado manual.
- Los seis casos activos sin antecedentes quedan como anomalías de
  compatibilidad. No se corrigen ni vinculan automáticamente.
- Una combinación simultánea de expropiación y comunidad indígena se declara
  inconsistente; no se aplica precedencia silenciosa.
- La salida terminal no es reversible por API en 2B. Una futura corrección
  administrativa queda fuera del subcorte y deberá ser compensatoria y
  auditable.
- Las ampliaciones individuales conservan los antecedentes originales porque
  las fuentes no prescriben reiniciar sensibilización/caminamiento.
- La ruta colectiva exige conclusión registral aplicable del acta y del COP;
  rol, pertenencia territorial y bloqueo posterior a terminal permanecen como
  reglas obligatorias.

No quedan decisiones funcionales abiertas que impidan diseñar o implementar
el Subcorte 2B. Los datos históricos ambiguos siguen sujetos a preflight y
conciliación, nunca a inferencia automática.

### 14.3 Reevaluación de gates

| Gate | Resultado | Evidencia en la propuesta corregida |
|---|---|---|
| Funcional | Superado | Las secciones 3, 5.3–5.5 y 14.1 definen cierre individual/colectivo y sustitución por modificatorio sin contradecir el flujo. |
| Datos | Superado a nivel de diseño | Las secciones 5.5, 6.1 y 8.2 definen ciclo, vigencia única, suma del linaje, límite por tipo, bloqueo concurrente y rechazo bajo lo pagado. |
| Seguridad | Superado a nivel de diseño | Las secciones 6.3 y 8 exigen autenticación, rol, pertenencia territorial, protección IDOR, errores seguros y auditoría. |
| Arquitectura | Superado | `tramo_nucleo` conserva antecedentes compartidos; `afectacion_ciclo` aísla ciclos posteriores; servicio de flujo centraliza transiciones sin invadir 2C. |
| Migración | Superado a nivel de diseño | La sección 7 define 006 expansiva, transaccional, respaldable, sin backfill inferido y con preflight de modificatorios, pagos y cierres. |
| Pruebas | Superado a nivel de estrategia | La sección 10 cubre secuencia, ambas rutas de cierre, modificatorios sucesivos, concurrencia, terminalidad, autorización, auditoría y regresión 2A. |

Esta aprobación corresponde al diseño. No afirma que código, migración o
pruebas estén implementados o ejecutados.

**Estado final de la propuesta: Propuesta viable y lista para implementación.**
