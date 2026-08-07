# Propuesta tecnica - Cierre financiero con pago suficiente

**Fecha:** 2026-08-04

**Estado:** propuesta tecnica; no implementada.

**Alcance:** endurecimiento de la regla de liberacion financiera del Corte
principal 2.

**Fuente de continuidad:** `ESTADO_PROYECTO.md`, `docs/Descripción proceso.md`,
`docs/Flujo liberacion derechos.md`, migracion 006 y auditoria puntual del
estado actual.

Esta propuesta no modifica codigo, no ejecuta migraciones y no cambia la base
de datos. Documenta el ajuste necesario para que "FIFONAFE hace el pago" quede
respaldado por evidencia financiera real en `pago_indemnizacion`.

## 1. Trabajo vigente identificado

El sistema ya implementa el flujo 2B/2C con estados derivados por afectación,
ciclos, RAN, FIFONAFE, pagos y subexpedientes. Además, el proyecto ha avanzado
completando la implementación local del **Corte 4** (autenticación formal por
sesiones con cookies Secure y mitigaciones CSRF) y el cierre técnico del
**Corte 5** (Dashboard analítico, uploader masivo GeoJSON para núcleos agrarios,
y el versionamiento de la franja del derecho de vía, aplicados hasta la migración 010).

La duda funcional vigente es si una afectacion debe considerarse liberada
cuando:

```text
FIFONAFE hace el pago
= debe existir pago registrado y suficiente
```

El comportamiento actual usa `tramite_fifonafe.estatus = 'completo'` como
evidencia de indemnizacion completa. La propuesta busca fortalecer esa regla
para que el estatus completo solo pueda existir si los pagos activos del ciclo
cubren el limite pagable vigente.

## 2. Estado actual verificado

### Regla funcional documentada

`ESTADO_PROYECTO.md` establece:

```text
sensibilizacion -> caminamiento -> afectacion confirmada -> asamblea,
solo para derechos colectivos -> convenio -> RAN -> FIFONAFE -> pago -> liberado
```

Tambien establece que una afectacion solo esta `liberada` despues de completar
el pago del flujo aplicable.

### Implementacion actual

La migracion 006 crea estados derivados en:

- `vw_afectacion_ciclo_estado`
- `vw_afectacion_estado`
- `vw_tramo_nucleo_estado`

En `vw_afectacion_ciclo_estado`, `indemnizacion_completa` se calcula hoy por
existencia de un tramite FIFONAFE activo:

```text
tramite_fifonafe.tipo_tramite = 'indemnizacion'
AND tramite_fifonafe.estatus = 'completo'
```

El calculo de estado financiero usa esa bandera:

```text
si indemnizacion_completa = false -> pendiente
si tipo_afectacion = colectivo y retiro_fondos_completo = false
  -> retiro_fondos_pendiente
en otro caso -> concluido
```

El servicio `completar_indemnizacion()` marca el tramite como `completo`, pero
no valida que exista un pago activo ni que el total pagado cubra el limite
pagable del ciclo.

`pago_indemnizacion` si valida:

- que el tramite sea de tipo `indemnizacion`;
- que exista informe de no conflictos completo y favorable;
- que exista limite financiero vigente;
- que el pago no exceda el saldo disponible.

Pero no existe una regla inversa que impida completar la indemnizacion sin pago
suficiente.

### Pruebas existentes

Actualmente hay pruebas que verifican:

- individual liberada cuando la indemnizacion se marca completa;
- colectivo no liberado hasta completar retiro de fondos;
- pagos no exceden el limite;
- modificatorio no reduce el limite por debajo de lo ya pagado.

Falta una prueba negativa explicita:

```text
intentar completar indemnizacion sin pago suficiente -> 409
```

## 3. Reglas funcionales confirmadas

1. RAN por si solo no libera una afectacion.
2. FIFONAFE forma parte del cierre financiero, pero debe estar respaldado por
   pago real.
3. La evidencia financiera operativa vive en `pago_indemnizacion`.
4. Individual no requiere asamblea de retiro de fondos.
5. Colectivo requiere, despues de indemnizacion completa, una asamblea de
   `retiro_fondos` completa del mismo ciclo.
6. El estado `liberada` debe derivarse, no capturarse manualmente.
7. No se debe usar `float` para dinero; todo monto debe seguir como `NUMERIC`
   en PostgreSQL y `Decimal` en Python.
8. No se deben corregir datos ambiguos silenciosamente.

## 4. Hallazgos y contradicciones

| ID | Hallazgo | Impacto | Clasificacion |
| --- | --- | --- | --- |
| H-01 | `indemnizacion_completa` depende de `tramite_fifonafe.estatus = 'completo'`, no de pagos suficientes. | Puede liberar una individual sin pago real registrado. | Critico funcional |
| H-02 | `completar_indemnizacion()` no valida `fn_2b_total_pagado_ciclo >= fn_2b_limite_ciclo`. | Permite cerrar financieramente con saldo pendiente. | Critico datos |
| H-03 | `fn_validar_pago_indemnizacion()` evita sobrepago, pero no obliga a cubrir el total antes del cierre. | El pago parcial puede coexistir con tramite completo si se marca por otra ruta. | Alto |
| H-04 | La no regresion de `tramite_fifonafe.estatus = 'completo'` impide revertir facilmente un cierre mal hecho. | Requiere preflight antes de endurecer reglas. | Alto |
| H-05 | Colectivo esta bien diferenciado: aun con indemnizacion completa exige retiro de fondos. | No requiere cambio conceptual, solo endurecer la evidencia de indemnizacion. | Correcto |

## 5. Diseno propuesto

Cambiar la regla de cierre financiero a:

```text
indemnizacion_completa(ciclo)
= existe tramite FIFONAFE de indemnizacion activo
  AND tramite.estatus = 'completo'
  AND fn_2b_total_pagado_ciclo(ciclo) >= fn_2b_limite_ciclo(ciclo)
```

El servicio y PostgreSQL deben impedir marcar una indemnizacion como completa si
no existe pago suficiente.

### Comportamiento esperado

#### Individual

```text
convenio COP original inscrito en RAN
-> informe de no conflictos completo y favorable
-> tramite de indemnizacion abierto
-> pago(s) registrados hasta cubrir limite pagable vigente
-> completar indemnizacion
-> estado_financiero = concluido
-> estado_liberacion = liberada
```

#### Colectivo

```text
asamblea de anuencia inscrita en RAN
-> convenio COP original inscrito en RAN
-> informe de no conflictos completo y favorable
-> tramite de indemnizacion abierto
-> pago(s) registrados hasta cubrir limite pagable vigente
-> completar indemnizacion
-> estado_financiero = retiro_fondos_pendiente
-> asamblea de retiro_fondos completa
-> estado_financiero = concluido
-> estado_liberacion = liberada
```

### Regla de suficiencia

```text
total_pagado_ciclo >= limite_pagable_ciclo
```

`total_pagado_ciclo` debe sumar pagos activos de tramites de indemnizacion del
mismo ciclo.

`limite_pagable_ciclo` debe seguir usando la version financiera vigente:

```text
colectivo:  monto_100 + monto_bdt
individual: monto_100
```

Cuando exista modificatorio vigente, el limite proviene del modificatorio
activo como ya lo hace `fn_2b_limite_ciclo`.

## 6. Cambios por capa

| Archivo o componente | Problema | Solucion | Justificacion | Dependencias | Riesgo | Validacion |
| --- | --- | --- | --- | --- | --- | --- |
| `backend/db/migrations/008_*_pago_suficiente.sql` | La base permite tramite completo sin pago suficiente. | Agregar funcion de validacion y reemplazar trigger/vistas 2B. | La integridad critica debe vivir tambien en PostgreSQL. | 006 y 007 aplicadas. | Datos existentes incompatibles. | Preflight y pruebas SQL/API. |
| `fn_2b_validar_fifonafe()` | No valida pagos al completar indemnizacion. | Si `NEW.tipo_tramite = 'indemnizacion'` y `NEW.estatus = 'completo'`, exigir `total_pagado >= limite`. | Evita cierre financiero sin evidencia. | `fn_2b_total_pagado_ciclo`, `fn_2b_limite_ciclo`. | Bloquea cierres historicos mal capturados. | Caso sin pago, parcial y suficiente. |
| `vw_afectacion_ciclo_estado` | `indemnizacion_completa` mira solo estatus. | Calcularla con estatus completo y pago suficiente. | La vista debe reflejar cierre financiero real. | Funciones 2B. | Cambian estados reportados. | Comparar antes/despues por fixtures. |
| `pago_indemnizacion` triggers | Una baja/edicion de pago podria dejar insuficiente un ciclo ya completo. | Impedir cambios que reduzcan total pagado debajo del limite cuando el tramite/ciclo ya esta completo. | Mantiene no regresion financiera. | Auditoria y baja logica existente. | Correcciones legitimas requeririan procedimiento administrativo. | Tests de update/baja logica. |
| `backend/app/services/flujo.py` | `completar_indemnizacion()` no valida suficiencia. | Consultar limite y total bajo lock del ciclo; devolver `409` si falta saldo. | Error de dominio claro antes del trigger. | Servicio 2B. | Mensajes nuevos para frontend. | Tests de servicio/API. |
| `backend/app/services/pagos.py` | Crea pagos pero no comunica que ya se puede completar. | Mantener captura de pagos; opcionalmente devolver estado actualizado en iteracion posterior. | Cambio minimo y compatible. | Ninguna. | Bajo. | Pruebas existentes. |
| `frontend/src/components/fase2/FlujoLiberacionPanel.jsx` | Boton "Completar indemnizacion" puede aparecer aunque falte saldo. | Deshabilitar o mostrar estado hasta `saldo_disponible = 0`; permitir completar solo con pago suficiente. | Evita frustracion, pero no sustituye backend. | Vista de estado. | Redondeos/Decimal en UI. | Build y prueba manual. |
| `frontend/src/components/fase2/PagosPanel.jsx` | Pago suficiente y accion de cierre estan separados. | Mostrar limite, total pagado y saldo; guiar captura antes de completar. | Hace visible la regla. | Estado del ciclo. | UX pendiente. | Validacion con usuarios. |
| `backend/tests/test_subcorte_2b.py` | No cubre cierre sin pago suficiente. | Agregar matriz de pagos insuficientes/suficientes individual y colectivo. | Previene regresion critica. | Fixtures validos 2B. | Medio. | Suite backend completa. |
| `ESTADO_PROYECTO.md` | Continuidad debe reflejar la regla despues de implementar. | Actualizar solo despues de migracion/pruebas. | Mantener fuente viva. | Implementacion validada. | Bajo. | Revision documental. |

## 7. Migracion y compatibilidad

La migracion debe ser expansiva y fortalecedora. No debe borrar datos ni
reclasificar pagos.

### Preflight obligatorio

Antes de modificar triggers/vistas, detectar:

```sql
SELECT tf.id_tramite_fifonafe,
       tf.id_afectacion,
       tf.id_ciclo_afectacion,
       fn_2b_limite_ciclo(tf.id_ciclo_afectacion) AS limite,
       fn_2b_total_pagado_ciclo(tf.id_ciclo_afectacion) AS pagado
  FROM tramite_fifonafe tf
 WHERE tf.activo = TRUE
   AND tf.tipo_tramite = 'indemnizacion'
   AND tf.estatus = 'completo'
   AND COALESCE(fn_2b_total_pagado_ciclo(tf.id_ciclo_afectacion), 0)
       < COALESCE(fn_2b_limite_ciclo(tf.id_ciclo_afectacion), 0);
```

Si hay filas, la migracion debe abortar con mensaje claro. Esas filas requieren
conciliacion manual:

- registrar pagos faltantes si el pago si existio;
- corregir el tramite si fue marcado completo indebidamente mediante proceso
  autorizado y auditable;
- no inferir pagos desde oficios, observaciones o montos de convenio.

### Compatibilidad

- Los pagos existentes se conservan.
- Los tramites incompletos se conservan.
- Las afectaciones liberadas solo por estatus de tramite pueden cambiar a
  `en_proceso` si no tienen pago suficiente; por eso se requiere preflight.
- No se deben hacer bajas fisicas.
- No se debe relajar la no regresion sin decision funcional explicita.

## 8. Seguridad, autorizacion e integridad

1. Mantener autorizacion por rol y pertenencia territorial.
2. Mantener `set_audit_context()` antes de escrituras auditables.
3. Mantener bloqueo de `afectacion_ciclo` al completar indemnizacion o registrar
   pagos para evitar condiciones de carrera.
4. Mantener pagos con `NUMERIC` y `Decimal`.
5. No exponer errores internos de PostgreSQL; mapear codigos 2B a mensajes de
   dominio.
6. La baja logica de pagos debe ser auditable y no puede romper un cierre
   financiero sin procedimiento definido.

## 9. Plan incremental de implementacion

1. Agregar pruebas rojas:
   - completar indemnizacion sin pagos;
   - completar con pago parcial;
   - completar con pago suficiente;
   - colectivo con pago suficiente sin retiro;
   - baja/edicion de pago que rompe suficiencia.
2. Crear migracion 008 con preflight y funciones/triggers/vistas actualizadas.
3. Actualizar servicio `completar_indemnizacion()` con validacion de suficiencia
   bajo lock.
4. Ajustar mensajes de dominio.
5. Ajustar frontend para guiar pago suficiente antes de completar.
6. Ejecutar pruebas 2B/2C y suite backend completa.
7. Ejecutar lint/build frontend.
8. Validar manualmente flujos individual y colectivo.
9. Actualizar `ESTADO_PROYECTO.md` solo con lo implementado y verificado.

## 10. Matriz de pruebas

| Area | Caso | Resultado esperado |
| --- | --- | --- |
| DB/API | Completar indemnizacion sin pagos | `409`, no cambia a `completo`, no libera. |
| DB/API | Pago parcial y completar indemnizacion | `409`, estado financiero sigue pendiente. |
| DB/API | Pago suficiente y completar indemnizacion individual | `estado_financiero = concluido`, `estado_liberacion = liberada`. |
| DB/API | RAN inscrito sin informe no conflictos | No permite indemnizacion/pago. |
| DB/API | Informe con conflictos | No permite indemnizacion/pago. |
| DB/API | Colectivo con pago suficiente e indemnizacion completa sin retiro | `retiro_fondos_pendiente`, no liberada. |
| DB/API | Colectivo con retiro de fondos completo | `estado_liberacion = liberada`. |
| DB/API | Baja logica de pago de ciclo concluido que deja total insuficiente | `409`. |
| DB/API | Modificatorio reduce limite bajo total pagado | `409`, conservar regla existente. |
| Concurrencia | Dos pagos concurrentes superan saldo | Solo uno puede cerrar; no hay sobrepago. |
| Frontend | Boton completar con saldo pendiente | Deshabilitado o error claro del backend. |
| Frontend | Saldo cero | Permite completar indemnizacion. |
| Regresion | Estados terminales | Siguen como `no_aplica_terminal`, no liberados. |
| Regresion | Subexpediente 2C | Pagos y estado siguen aislados por afectacion. |

## 11. Riesgos y mitigaciones

| Riesgo | Mitigacion |
| --- | --- |
| Datos existentes con tramites completos sin pagos suficientes. | Preflight abortivo y conciliacion manual antes de migrar. |
| Usuarios han usado `estatus = completo` como sustituto administrativo del pago. | Validacion funcional y capacitacion; UI debe mostrar saldo y pagos requeridos. |
| Correccion de pagos despues de cierre. | Definir procedimiento: ajuste compensatorio o permiso especial; no baja fisica. |
| Redondeos monetarios. | Usar `NUMERIC`/`Decimal`; comparar con escala definida, no `float`. |
| Cambio de reportes historicos. | Documentar diferencia entre "tramite completo" y "pago suficiente". |
| Condiciones de carrera en pagos. | Bloquear `afectacion_ciclo` y mantener triggers de limite. |

## 12. Criterios de aceptacion

1. No se puede completar una indemnizacion sin pago suficiente.
2. Una individual solo queda `liberada` con RAN, informe no conflictos,
   indemnizacion completa y pagos suficientes.
3. Una colectiva con indemnizacion completa y pagos suficientes queda en
   `retiro_fondos_pendiente` hasta completar la asamblea de retiro.
4. La vista `vw_afectacion_estado` no reporta `liberada` si el pago es parcial.
5. Las bajas o ediciones de pagos no pueden invalidar silenciosamente un ciclo
   concluido.
6. Todos los cambios son auditables.
7. La migracion aborta si detecta cierres historicos incompatibles.
8. Las pruebas backend 2B/2C y la suite completa pasan.
9. El frontend muestra saldo/total pagado de forma coherente y no induce a
   completar sin pago suficiente.

## 13. Actualizaciones previstas para `ESTADO_PROYECTO.md`

Despues de implementar y validar, actualizar:

- reglas obligatorias de cierre financiero;
- historial de migraciones con 008;
- trabajo realizado del ajuste de pago suficiente;
- pruebas ejecutadas;
- riesgos restantes y procedimiento por ambiente;
- instruccion para continuar.

No actualizar documentos historicos como roadmap vigente.

## 14. Decisiones que requieren aprobacion

1. Confirmar que "FIFONAFE hace el pago" significa pago registrado suficiente
   en `pago_indemnizacion`, no solo oficio o estatus administrativo.
2. Confirmar si el pago suficiente debe ser `>= limite_pagable` exacto o si se
   permite tolerancia por centavos/redondeo. Recomendacion: sin tolerancia
   mientras todos los montos sean `NUMERIC(18,2)`.
3. Confirmar procedimiento para corregir pagos despues de cierre:
   - bloquear cualquier reduccion que deje insuficiente el ciclo, o
   - permitir ajuste solo mediante operacion administrativa especial futura.
4. Confirmar que tramites actualmente completos sin pago suficiente deben
   conciliarse manualmente antes de migrar; no se deben corregir en automatico.
5. Confirmar si la UI debe permitir capturar pago y completar indemnizacion en
   una sola accion transaccional futura o mantenerlo como dos acciones separadas.
