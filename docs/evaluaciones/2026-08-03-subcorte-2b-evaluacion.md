# Evaluación técnica — Subcorte 2B

**Fecha:** 2026-08-03

**Propuesta evaluada:** `docs/propuestas/2026-08-03-subcorte-2b-propuesta.md`

**Rama observada:** `feature/backend-logica`
**Estado de la evaluación:** concluida; implementación no iniciada

## 1. Trabajo vigente identificado

`ESTADO_PROYECTO.md` identifica como siguiente trabajo el **Subcorte 2B del
Corte principal 2: secuencia, salidas terminales y estado de liberación por
afectación**.

El alcance vigente comprende:

- enlazar las etapas existentes para impedir saltos;
- registrar salidas terminales por afectación y agregarlas en
  `tramo_nucleo`;
- separar progreso operativo, registral, financiero, terminal y liberación;
- derivar `liberado` después del pago aplicable;
- cubrir rutas colectiva, individual, terminal y expediente mixto.

No comprende la navegación y aislamiento documental completo de 2C, el
derecho de vía versionado del Corte 5, propiedad privada, catastro, Registro
Público, avalúos ni el seguimiento externo de expropiaciones o comunidades
indígenas.

## 2. Resumen de la propuesta evaluada

La propuesta plantea una migración expansiva 006, estados derivados por
afectación, controles de secuencia en servicio y PostgreSQL, salida terminal,
agregación corregida, autorización territorial, adaptación del frontend y una
matriz amplia de pruebas.

Su orientación general es correcta: conserva `tramo_nucleo` como expediente
maestro, evita una bandera manual de liberación, mantiene dinero exacto,
propone transacciones atómicas, no elimina datos existentes y separa RAN de
liberación.

La versión original, sin embargo, contenía dos supuestos no sustentados y una
carencia estructural:

1. Interpretaba que el pago concluye al alcanzar exactamente el límite
   `monto_100 + monto_bdt`, aunque las fuentes sólo definen esa suma como
   máximo y el esquema contiene `tipo_pago='total'`.
2. Proponía asociar directamente todas las actividades de campo a una
   afectación, en conflicto con su carácter compartido y previo a la creación
   de `afectacion`.
3. No proporcionaba una identidad estable para distinguir múltiples ciclos
   posteriores del mismo tipo.

La propuesta fue corregida durante esta auditoría para no convertir esos
supuestos en reglas implementables.

## 3. Hallazgos de auditoría

### 3.1 Coherencia funcional

- El flujo ordinario de la propuesta coincide con el flujograma, la
  descripción canónica y Requirement 37.
- La ruta colectiva debe tener asamblea ligada a una afectación colectiva;
  Requirement 7 lo establece expresamente. Esta relación no necesita una
  nueva decisión funcional.
- Sensibilización y caminamiento originales pertenecen a `tramo_nucleo` y
  ocurren antes de crear la afectación. Un `id_afectacion` directo en toda
  actividad habría contradicho Requirements 5 y 6.
- Superficie adicional y obras complementarias sí abren nuevos ciclos
  completos. `contexto_proceso` no identifica dos ciclos del mismo tipo, por
  lo que hace falta una clave de ciclo o una estructura equivalente.
- Ampliación y ampliación remanente individuales registran superficie, montos
  y seguimiento RAN. Las fuentes no ordenan reiniciar sensibilización y
  caminamiento; exigirlo inventaría una regla.
- Para la ruta colectiva, el flujograma y los requisitos exigen seguimiento
  RAN tanto del acta como del COP. No es una decisión abierta.

### 3.2 Integridad financiera

- `monto_100 + monto_bdt` es el **límite pagable**, no necesariamente el
  importe que prueba el cierre. `monto_90` está incluido en `monto_100`.
- `pago_indemnizacion.tipo_pago` admite `anticipo`, `parcial` y `total`, y el
  esquema permite un único pago total activo por trámite.
- `tramite_fifonafe.estatus` admite `completo`, pero las fuentes no fijan si la
  liberación exige el trámite completo, un pago `total`, ambos o una evidencia
  distinta.
- El trigger vigente serializa por trámite FIFONAFE y limita pagos contra el
  convenio exacto. No define cómo un modificatorio altera la obligación del
  padre, el saldo o los pagos previos.
- Elegir igualdad contra el máximo, “último modificatorio activo” o bolsas
  independientes cambiaría resultados financieros. Son decisiones
  indispensables y no verificables en el repositorio.

### 3.3 Esquema y compatibilidad

La base activa fue consultada sólo en lectura y confirmó:

| Evidencia | Resultado |
|---|---:|
| Migraciones registradas | 004 y 005 |
| Afectaciones activas | 6 |
| Actividades realizadas activas | 0 |
| Pagos activos | 0 |
| Campo terminal en `afectacion` | no existe |
| `asamblea.id_afectacion` | no existe |
| `actividad_campo.id_afectacion` | no existe |
| `vw_afectacion_estado` | no existe |
| Asignaciones territoriales activas | 7 |

Las seis afectaciones activas no tienen los antecedentes que una regla 2B
exigiría. No deben corregirse, asociarse ni completarse automáticamente. La
estrategia expansiva y el preflight propuestos son apropiados, pero la
migración no puede diseñar todavía las invariantes financieras definitivas.

### 3.4 Backend y contratos

- Los endpoints heredados en `backend/app/main.py` concentran lógica parcial y
  permiten crear/actualizar etapas sin máquina de transición común.
- La FK compuesta de convenio protege afectación, expediente y tipo, pero la
  asamblea sólo se verifica contra el mismo `tramo_nucleo`.
- FIFONAFE permite referencias nulas/parciales y no relaciona de forma
  explícita la indemnización con el informe de no conflictos que la habilita.
- El servicio de pagos usa `Decimal` y contexto de auditoría, pero no verifica
  RAN, informe de no conflictos o terminalidad.
- Los handlers de `InternalError` e `IntegrityError` devuelven texto derivado
  de `exc.orig`; limpiarlo parcialmente no satisface la regla de no exponer
  errores internos.

### 3.5 Seguridad y autorización

- `RoleChecker` valida rol, pero no pertenencia territorial.
- `usuario_tramo` existe y tiene asignaciones activas, pero no filtra las
  lecturas ni protege escrituras por recurso.
- El rol geógrafo puede ejecutar múltiples escrituras no geoespaciales en
  `main.py`, contrario a Requirement 1.
- La propuesta acierta al exigir una resolución central de acceso territorial
  y protección contra IDOR. Debe aplicarse a todas las rutas que puedan leer o
  modificar el flujo 2B, incluidos endpoints heredados alternativos.

### 3.6 Frontend y pruebas

- El frontend no captura sensibilización/caminamiento ni el circuito completo
  de FIFONAFE/no conflictos.
- `PagosPanel.jsx` calcula sumas informativas con `Number` y ofrece trámites
  sin una elegibilidad autoritativa del backend.
- Tablero y mapa heredan la clasificación RAN como liberación.
- Las fixtures actuales crean afectaciones y pagos saltando etapas. Deben
  migrarse a fábricas de flujo válido sin desactivar las pruebas negativas.
- No se ejecutó la suite porque no hubo implementación y la suite actual
  realiza escrituras en la base compartida. No se declara validación dinámica.

## 4. Matriz de evaluación

| Área | Resultado | Evidencia | Ajuste requerido |
|---|---|---|---|
| Alcance de 2B | Aprobada | Coincide con `ESTADO_PROYECTO.md`, sección 8, Subcorte 2B. | Mantener 2C y Corte 5 fuera. |
| Secuencia ordinaria | Aprobada | `docs/Descripción proceso.md`, `docs/Flujo liberacion derechos.md` y Requirement 37. | Implementar sólo después de cerrar los bloqueos financieros. |
| Estados separados | Aprobada con ajustes | Requirement 37.7 exige operativo, registral, financiero y terminal. | Congelar nombres y precedencias antes de crear vistas. |
| Liberación posterior al pago | Pendiente de validación | Las fuentes exigen pago aplicable completado, pero no definen evidencia ejecutable de cierre. | Resolver D-01. |
| Asociación de asamblea | Aprobada con ajustes | Requirement 7.1 exige afectación colectiva; esquema actual carece de FK. | Añadir vínculo a afectación y ciclo sin inferir datos históricos. |
| Asociación directa de actividad a afectación | Rechazada | Requirements 5/6 y descripción canónica conservan antecedentes originales en `tramo_nucleo`. | Mantener originales compartidos; usar ciclo sólo para variantes posteriores. |
| Identidad de ciclo posterior | Aprobada con ajustes | Superficie adicional/obras pueden repetirse y `contexto_proceso` es sólo textual. | Aprobar `afectacion_ciclo` o estructura equivalente. |
| Ampliaciones individuales | Aprobada con ajustes | La fuente exige superficie, monto y RAN, no un nuevo ciclo social. | Reutilizar antecedentes originales; no inventar sensibilización/caminamiento. |
| Linaje modificatorio | Pendiente de validación | FK padre existe, pero no hay regla de sustitución de importe/saldo. | Resolver D-04 antes de permitir pagos/liberación por ciclos modificados. |
| Límite y concurrencia de pagos | Aprobada con ajustes | Trigger 004 usa `NUMERIC` y bloqueo asesor por trámite. | Conservar protección actual; ampliar bloqueo sólo con semántica D-04 aprobada. |
| Salidas terminales | Aprobada con ajustes | Requirement 19 define niveles y bloqueo posterior. | Añadir afectación, detectar conflictos entre niveles y definir corrección auditada. |
| Migración expansiva | Aprobada con ajustes | 004/005 activas; seis afectaciones históricas incompletas. | No redactar 006 final hasta cerrar invariantes; columnas nulas, preflight y sin backfill inferido. |
| ORM y contratos | Aprobada con ajustes | Modelos reflejan esquema actual, contratos permiten saltos. | DTO de transición y estado; no reutilizar CRUD genérico para terminalidad. |
| Servicios transaccionales | Aprobada con ajustes | Existe `set_audit_context`; lógica 2B está dispersa. | Servicio de flujo central, una transacción y errores de dominio seguros. |
| Endpoints | Aprobada con ajustes | Hay rutas heredadas alternativas en `main.py`. | Evitar bypass y duplicados; conservar compatibilidad mediante delegación. |
| Autorización territorial | Aprobada | Requirement 1.7 y regla obligatoria de continuidad. | Resolver tramo desde cada recurso, filtrar listas y probar IDOR. |
| Separación de rol geógrafo | Aprobada | Requirement 1.4 limita escritura a geometrías/datos geoespaciales. | Retirarlo de escrituras de negocio 2B con transición de asignaciones. |
| Auditoría | Aprobada | Mecanismo existente con `SET LOCAL`. | Exigirlo antes de toda escritura 2B, incluida corrección terminal. |
| Manejo de errores | Aprobada con ajustes | `main.py` aún deriva respuestas de `exc.orig`. | Mapear constraints conocidas y mantener detalles sólo en logs. |
| Frontend | Aprobada con ajustes | Faltan actividades/FIFONAFE y estados correctos. | UI mínima 2B; no implementar todavía navegación documental de 2C. |
| Estrategia de pruebas | Aprobada | Cubre DB, API, seguridad, frontend, concurrencia y regresión. | Base aislada y fixtures secuenciales; agregar casos de decisiones aprobadas. |
| Actualización de continuidad | Aprobada | La propuesta la condiciona a implementación validada. | No modificar `ESTADO_PROYECTO.md` en estado bloqueado. |

## 5. Resultado de los gates

| Gate | Resultado | Fundamentación |
|---|---|---|
| Funcional | **No superado** | No está definido qué evidencia hace que un pago esté concluido ni cómo actúa un modificatorio sobre la obligación económica. Ambas reglas determinan `liberada`. |
| Datos | **No superado** | Sin esas reglas no puede construirse una restricción correcta de saldo, linaje y liberación. Además, la identidad de ciclo posterior requiere aprobación de diseño. |
| Seguridad | Superable con ajustes | El diseño propuesto cubre rol, territorio, IDOR, auditoría y errores; la implementación actual todavía no. |
| Arquitectura | Superable con ajustes | Debe reemplazarse la FK directa de actividad por una identidad de ciclo posterior y delegar rutas heredadas al servicio central. |
| Migración | **No superado** | La estrategia es expansiva, pero 006 no puede congelar invariantes financieras no aprobadas. |
| Pruebas | Superable con ajustes | La matriz es suficiente como estrategia, pero necesita reglas finales y una base aislada antes de convertirse en pruebas ejecutables. |

Al fallar de manera crítica los gates funcional, de datos y de migración, las
reglas de la tarea obligan a detenerse antes de implementar.

## 6. Propuesta corregida

Se corrigió
`docs/propuestas/2026-08-03-subcorte-2b-propuesta.md` de esta forma:

1. Ya no equipara pago concluido con alcanzar exactamente el máximo pagable.
2. Conserva sensibilización/caminamiento originales en `tramo_nucleo`.
3. Sustituye `actividad_campo.id_afectacion` por una referencia opcional a
   `afectacion_ciclo` sólo para ciclos posteriores.
4. Vincula las nuevas asambleas de autorización a afectación colectiva y
   ciclo, conforme a Requirement 7.
5. Introduce `afectacion_ciclo` como identidad técnica, sin estado manual,
   para distinguir variantes repetibles.
6. No atribuye a ampliaciones individuales un reinicio social no documentado.
7. No asume la revisión monetaria vigente ni agrega pagos padre/modificatorio
   antes de resolver su semántica.
8. Reduce las decisiones abiertas: rol/territorio, RAN colectivo y bloqueo
   posterior a terminal ya eran obligatorios y no se reabren.

La propuesta corregida permanece como diseño condicionado; no es una
autorización de implementación.

## 7. Decisión de viabilidad

La propuesta es **funcionalmente prometedora pero actualmente no viable para
implementación completa**.

Bloqueos indispensables:

- **D-01 — Pago concluido:** precisar si el cierre exige
  `pago_indemnizacion.tipo_pago='total'`, `tramite_fifonafe.estatus='completo'`,
  ambos u otra evidencia. El límite económico no demuestra por sí solo el
  cierre.
- **D-04 — Modificatorio financiero:** precisar si sustituye los montos del
  padre, su vigencia, el tratamiento de pagos previos y el saldo resultante.

Decisiones de diseño necesarias antes de migrar:

- aprobar `afectacion_ciclo` o una alternativa que distinga ciclos
  posteriores repetibles;
- definir el procedimiento administrativo de corrección de una salida
  terminal, sin reabrir el flujo mediante CRUD genérico.

No se implementaron pruebas, migración, ORM, contratos, servicios, endpoints
ni frontend.

## 8. Plan final de implementación

Plan condicionado a resolver los bloqueos:

1. Registrar las respuestas funcionales D-01 y D-04 en la propuesta y en
   criterios de prueba, sin modificar aún el estado de continuidad.
2. Aprobar el diseño de `afectacion_ciclo` y la corrección terminal.
3. Crear una base de pruebas aislada desde migraciones 001–005 y ejecutar el
   preflight sobre una copia representativa.
4. Escribir primero pruebas negativas/positivas de secuencia, estados,
   finanzas, terminalidad, rol y territorio.
5. Crear la migración expansiva 006 y validarla dentro de transacciones de
   prueba, incluido rollback y concurrencia.
6. Implementar ORM y contratos de transición.
7. Implementar servicios transaccionales y acceso territorial central.
8. Delegar endpoints heredados al servicio, sin rutas duplicadas ni bypass.
9. Implementar la UI mínima 2B y corregir métricas de tablero/mapa.
10. Ejecutar suite backend, pruebas SQL, frontend, build e integración.
11. Conciliar datos históricos sin inferencias y validar constraints
    diferidas cuando corresponda.
12. Actualizar `ESTADO_PROYECTO.md` sólo con resultados ejecutados y
    comprobados.

## 9. Cambios realizados

No hubo implementación.

| Archivo | Cambio | Justificación |
|---|---|---|
| `docs/propuestas/2026-08-03-subcorte-2b-propuesta.md` | Corrección del diseño de ciclos, actividades y decisiones financieras. | Evitar cardinalidad incorrecta y reglas económicas no documentadas. |
| `docs/evaluaciones/2026-08-03-subcorte-2b-evaluacion.md` | Registro de esta evaluación. | Trazabilidad exigida por la tarea. |

No se modificaron archivos de código, migraciones ni configuración.

## 10. Migraciones y compatibilidad

No se creó ni ejecutó migración. La base activa permanece con `004` y `005`.

La futura 006 deberá ser expansiva, transaccional y no destructiva, pero no
debe redactarse como definitiva hasta resolver D-01 y D-04. Los seis casos
activos sin actividades realizadas deberán aparecer en el preflight; no se
les asignarán antecedentes, ciclos ni estados concluidos automáticamente.

## 11. Pruebas y validaciones

| Validación | Comando | Resultado | Estado |
|---|---|---|---|
| Estado inicial de Git | `git status --short && git branch --show-current` | Rama `feature/backend-logica`; sólo existía la propuesta nueva sin seguimiento. | Ejecutada |
| Lectura de continuidad | `sed` por rangos sobre `ESTADO_PROYECTO.md` | 714 líneas revisadas; siguiente trabajo 2B confirmado. | Ejecutada |
| Contraste funcional | `pdftotext` y lectura de documentos canónicos/requisitos | Secuencia y terminalidad confirmadas; cierre financiero no definido de forma ejecutable. | Ejecutada |
| Esquema activo | `docker exec ... psql ... -Atc` con consultas `SELECT` | Versiones 004/005, 6 afectaciones activas, 0 actividades realizadas y ausencia de estructuras 2B. | Ejecutada, sólo lectura |
| Revisión estática de capas | `rg`/`sed` sobre migraciones, modelos, contratos, servicios, endpoints, frontend y pruebas | Se confirmaron los hallazgos descritos en las secciones 3 y 4. | Ejecutada |
| Suite backend | No ejecutada | No hubo implementación y la suite actual escribe en la base compartida. | No ejecutada |
| Pruebas frontend/build | No ejecutadas | No hubo cambios de frontend. | No ejecutada |
| Migración 006 | No ejecutada | No existe y los gates impiden crearla/aplicarla. | No ejecutada |

## 12. Riesgos restantes

- Liberar anticipadamente una afectación si se interpreta incorrectamente
  `total`, `completo` o el máximo pagable.
- Duplicar capacidad económica o calcular un saldo incorrecto al introducir
  modificatorios.
- Mezclar dos superficies adicionales/obras complementarias si no existe una
  identidad de ciclo estable.
- Bloquear datos existentes si se validan antecedentes históricos sin
  conciliación.
- Mantener IDOR territorial y privilegios excesivos del geógrafo mientras 2B
  no se implemente.
- Continuar exponiendo mensajes derivados de PostgreSQL en errores manejados.
- Mantener cifras de liberación incorrectas en tablero/mapa hasta reemplazar
  las vistas vigentes.

## 13. Actualización realizada en `ESTADO_PROYECTO.md`

Ninguna. El archivo no debe marcar 2B como terminado ni registrar una
migración inexistente. Sólo se actualizará después de una implementación
completa y de validaciones dinámicas reproducibles.

## 14. Estado final

**Propuesta bloqueada por decisión funcional.**

La evidencia del repositorio permite aprobar el alcance, la secuencia general,
las salidas terminales, la autorización territorial y la estrategia
expansiva. No permite decidir qué prueba el cierre del pago ni cómo un
modificatorio altera la obligación y los pagos del convenio padre. Estas dos
reglas afectan directamente liberación, saldo, concurrencia e integridad en
PostgreSQL; implementarlas sin aprobación violaría los gates funcional, de
datos y de migración.
