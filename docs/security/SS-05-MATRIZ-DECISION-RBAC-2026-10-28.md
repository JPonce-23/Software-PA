# SS-05, fase 0: matriz de decisión RBAC documental

Fecha: 2026-10-28. `dev`, SHA `683ff75613768de28a7127c7e33a6e2ef4fc40ff` más correcciones locales previas preservadas. **Actual** describe código; **C propuesto** requiere aprobación. Este documento no concede permisos.

Ver [análisis y evidencia](SS-05-ANALISIS-POLITICA-DOCUMENTAL-2026-10-28.md) y [plan/decisiones](SS-05-PLAN-IMPLEMENTACION-2026-10-28.md).

## Convenciones

D activo, V1/V2 existentes, vínculos LA/LB a objetivos exclusivos A/B activos, proyectos y ascendencia activos. Las columnas “sólo A”, “sólo B”, “A+B” y “ninguno” se refieren al **alcance efectivo de autorización**, no al mero contenido de UsuarioProyecto. Se añade el cruce por asignación real para no inventar una limitación que el código no tiene.

- M: consulta de metadatos; V: lista de versiones; Dv: descarga de versión; Cn: consulta consolidada por PN.
- G: modificación global de metadatos **y** carga de nueva versión (ambas se detallan en el análisis).
- L+: agregar otro vínculo; U: desvinculación individual; BG: baja global.
- Sí requiere que el recurso exista, la cadena autorice y las demás validaciones de formato/ruta/esquema se cumplan. No implica descarga exitosa si falta el archivo.
- Denegado indica política/rol; no se fija automáticamente un nuevo contrato de códigos 403/404. Hoy D inactivo404, sin vínculos activos409 y sin alcance403 en el helper documental.

## Matriz actual: rol × asignación registrada

Admin/visualizador/geógrafo obtienen lectura de proyectos activos sin necesitar asignación; “ninguno asignado” no significa “sin acceso”. Para admin la captura es global sobre proyectos activos. Visualizador/geógrafo nunca capturan documentos. Esas reglas no se modifican.

| Rol | Asignación ilustrativa | Alcance efectivo sobre A/B | M/V/Dv de D | G | L+ | BG | U | Cn |
|---|---|---|---|---|---|---|---|---|
| Admin | Sólo A | A+B | Sí, todas versiones | Sí | Sí si destino resoluble | Sí, afecta A+B | No existe ruta | A y B |
| Admin | Sólo B | A+B | Sí, todas versiones | Sí | Sí si destino resoluble | Sí, afecta A+B | No existe ruta | A y B |
| Admin | A+B | A+B | Sí, todas versiones | Sí | Sí si destino resoluble | Sí, afecta A+B | No existe ruta | A y B |
| Admin | Ninguna | A+B | Sí, todas versiones | Sí | Sí si destino resoluble | Sí, afecta A+B | No existe ruta | A y B |
| Operador | Sólo A | A | Sí, todas versiones | Sí, afecta A+B | Sólo destino con alguna captura A | Sí, afecta A+B | No existe ruta | Sólo A |
| Operador | Sólo B | B | Sí, todas versiones | Sí, afecta A+B | Sólo destino con alguna captura B | Sí, afecta A+B | No existe ruta | Sólo B |
| Operador | A+B | A+B | Sí, todas versiones | Sí, afecta A+B | Destino con alguna captura A/B | Sí, afecta A+B | No existe ruta | A y B |
| Operador | Ninguna | Ninguno | Denegado | Denegado | Denegado | Denegado | No existe ruta | Denegado |
| Visualizador | Sólo A | A+B lectura | Sí, todas versiones | Denegado | Denegado | Denegado | No existe ruta | A y B |
| Visualizador | Sólo B | A+B lectura | Sí, todas versiones | Denegado | Denegado | Denegado | No existe ruta | A y B |
| Visualizador | A+B | A+B lectura | Sí, todas versiones | Denegado | Denegado | Denegado | No existe ruta | A y B |
| Visualizador | Ninguna | A+B lectura | Sí, todas versiones | Denegado | Denegado | Denegado | No existe ruta | A y B |
| Geógrafo | Sólo A | A+B lectura | Sí, todas versiones | Denegado | Denegado | Denegado | No existe ruta | A y B |
| Geógrafo | Sólo B | A+B lectura | Sí, todas versiones | Denegado | Denegado | Denegado | No existe ruta | A y B |
| Geógrafo | A+B | A+B lectura | Sí, todas versiones | Denegado | Denegado | Denegado | No existe ruta | A y B |
| Geógrafo | Ninguna | A+B lectura | Sí, todas versiones | Denegado | Denegado | Denegado | No existe ruta | A y B |

Un admin activo “sin acceso efectivo a A ni B”, o un visualizador/geógrafo con acceso efectivo sólo A, no son escenarios disponibles con ambos proyectos activos bajo este código. Si la cuenta no está activa/autenticada, falla antes de esta matriz. No simular otro rol/alcance y presentarlo como resultado del producto.

## Matriz actual: vínculos inactivos, versiones anteriores y reasignaciones

| Escenario | Admin | Operador sólo A | Operador sólo B | Operador A+B | Visualizador / geógrafo |
|---|---|---|---|---|---|
| LA inactivo, LB activo | Lee/captura por B | D denegado salvo otra ruta; consolidado A no incluye LA | Lee/captura por B | Lee/captura por B | Lectura por B; sin captura |
| LB inactivo, LA activo | Lee/captura por A | Lee/captura por A | D denegado salvo otra ruta | Lee/captura por A | Lectura por A; sin captura |
| Ambos vínculos inactivos | D409 por ruta ordinaria | D409 | D409 | D409 | D409 |
| V1/V2 cargadas antes de LA | Lee ambas si D autoriza | Lee ambas por LA actual | Lee ambas por LB actual | Lee ambas | Lee ambas por vínculo actual |
| V1/V2 cargadas antes de LB | Lee ambas si D autoriza | Lee ambas por LA actual | Lee ambas por LB actual | Lee ambas | Lee ambas por vínculo actual |
| Proyecto B inactivo, LA activo | D por A; Cn-B denegado | D por A | Sin A, denegado | D por A | D por A; Cn-B denegado |
| Vínculo único a núcleo N que deriva A+B | Lectura/captura | Lectura/captura por A | Lectura/captura por B | Lectura/captura | Lectura por un proyecto activo; sin captura |
| Operador pierde A y no tiene B | No aplica a admin | Nueva solicitud denegada | No cambia | Si conserva B, D sigue accesible | Asignaciones no determinan lectura global |
| Operador gana B | No altera alcance global | Accede por B incluso al histórico anterior | Ya tenía B | Sigue accediendo | No altera lectura global |
| D inactivo por baja global | 404 ordinario | 404 | 404 | 404 | 404 |

Inactivo no significa borrado; no se eliminan bytes ni referencias por estas ramas. Si LA apunta a un núcleo compartido A+B, no es “vínculo exclusivo A”: deben aplicarse todos los proyectos derivados, no esta abreviatura.

## Modelo A: reglas candidatas, aún no aprobadas

| Acción | Sólo captura A o sólo B | Captura A+B | Admin | Sólo lectura |
|---|---|---|---|---|
| M, V, Dv | Todas versiones con cualquier vínculo autorizado | Todas versiones | Todas por ruta ordinaria activa | Todas con un vínculo legible |
| Metadatos / nueva versión | No, porque impacta A+B | Sí si cubre todos los ámbitos afectados | Sí con facultad global explícita | No |
| L+ a otro expediente | No si no cubre conjunto anterior y destino | Sólo si también cubre destino y éste consiente | Revisión de compartición | No |
| U local | Propuesta: sólo ámbito propio, dependencias resueltas | Sólo vínculo elegido | Motivo y dependencias | No |
| BG | No | Requiere decisión: todos los ámbitos o admin | Sí mediante acción explícita | No |

A implica deliberadamente exposición de todo el historial pasado/futuro. No puede combinarse en la práctica con promesa de versiones privadas por vínculo. Debe fijarse el trato de ámbitos inactivos y referencias antes de implementar “todos”.

## Modelo B: reglas candidatas, aún no aprobadas

| Acción | Sólo A | Sólo B | A+B | Admin | Sólo lectura |
|---|---|---|---|---|---|
| M, V, Dv | Unidad documental A | Unidad documental B | Ambas unidades separadas | Según ámbito administrativo | Unidad en ámbito legible |
| Metadatos / nueva versión | Sólo unidad A | Sólo unidad B | Cada unidad independiente | Unidad indicada | No |
| L+ a otro expediente | Derivado/publicación autorizada; no compartir automáticamente historial | Igual | Separación de unidades y procedencia | Operación registrada | No |
| U / baja local | Sólo contexto A con dependencias | Sólo B | Contexto seleccionado | Contexto seleccionado | No |
| BG entre unidades | No existe una baja cruzada implícita | Igual | Igual | Procedimiento expreso de retención | No |

B necesita un nuevo modelo de pertenencia y migración; el backend actual no puede aplicarlo cambiando sólo un `any` por `all`.

## Modelo C recomendado: reglas normativas propuestas

Para D explícitamente compartido A+B, definir:

- `Pguard(D)`: participantes activos o suspendidos; se conservan en protección los ámbitos inactivos y retiros con referencias/evidencia sin resolución formal. No inferir permiso por conjunto vacío. Alcance ambiguo ⇒ revisión administrativa.
- `S(u)`: ámbitos con captura actual; proyecto inactivo no se convierte en permiso de operador.
- `Q(s,D)`: conjunto explícito de versiones publicadas/aprobadas para el ámbito s. Puede contener V1, V2, ambas o ninguna; no es rango de fechas ni “todas por defecto”.
- `R(s)`: lectura actual del ámbito; `W(s)`: captura actual más política funcional aplicable.
- Administración explícita no equivale a ignorar motivos, dependencia, política de retención o trazabilidad.

Un documento privado tiene un ámbito de seguridad declarado; no puede servir como D multiexpediente hasta una decisión de promoción o derivación. Para D compartido, proponer `G = rol admin con facultad explícita` o `rol operador y Pguard no vacío y Pguard ⊆ S(u)`, siempre con decisiones de compartición vigentes. La baja global se reserva a admin. Un operador con A+B no otorga consentimiento funcional por el mero hecho de tener ambas asignaciones.

### Cruce rol × alcance efectivo (C propuesto, no ejecutado)

| Rol | Alcance efectivo planteado | M | V/Dv | G | L+ | U local | BG | Cn |
|---|---|---|---|---|---|---|---|---|
| Admin | Sólo A | No aplicable con admin global actual | No aplicable | No aplicable | No aplicable | No aplicable | No aplicable | No aplicable |
| Admin | Sólo B | No aplicable con admin global actual | No aplicable | No aplicable | No aplicable | No aplicable | No aplicable | No aplicable |
| Admin | A+B global | Global autorizado; contexto histórico en flujo separado | Administrativa explícita; no publicar a terceros por descargar | Sí explícito | Sí con aprobación de participantes/destino | Sí con motivo/dependencias | Sólo flujo administrativo | Contexto autorizado |
| Admin | Ninguno | No aplicable con cuenta admin activa y proyectos activos | No aplicable | No aplicable | No aplicable | No aplicable | No aplicable | No aplicable |
| Operador | Sólo A | Global compartible + local A | Sólo Q(A,D) | No | Solicitar; no ampliar audiencia por sí solo | Sólo LA exclusivo, con dependencias resueltas | No | Sólo A, latest aprobado A |
| Operador | Sólo B | Global compartible + local B | Sólo Q(B,D) | No | Solicitar; no ampliar audiencia por sí solo | Sólo LB exclusivo, con dependencias resueltas | No | Sólo B, latest aprobado B |
| Operador | A+B | Global compartible + contextos autorizados | Q del contexto solicitado, sin unión implícita | Sí si Pguard cubierto y decisiones vigentes | Si cubre Pguard/destino y compartición aprobada | Vínculo/ámbito seleccionado | No | Por contexto, no max global |
| Operador | Ninguno | No | No | No | No | No | No | No |
| Visualizador | Sólo A | Contrafactual a política actual; si algún día se aprueba: contexto A | Q(A,D) | No | No | No | No | Sólo A hipotético |
| Visualizador | Sólo B | Contrafactual; contexto B | Q(B,D) | No | No | No | No | Sólo B hipotético |
| Visualizador | A+B lectura | Compartible + contexto leído | Q de cada contexto legible | No | No | No | No | Por contexto |
| Visualizador | Ninguno | Contrafactual; denegar | No | No | No | No | No | No |
| Geógrafo | Sólo A | Contrafactual a política actual; contexto A | Q(A,D) | No | No | No | No | Sólo A hipotético |
| Geógrafo | Sólo B | Contrafactual; contexto B | Q(B,D) | No | No | No | No | Sólo B hipotético |
| Geógrafo | A+B lectura | Compartible + contexto leído | Q de cada contexto legible | No | No | No | No | Por contexto |
| Geógrafo | Ninguno | Contrafactual; denegar | No | No | No | No | No | No |

La propuesta **no restringe por asignaciones** el rol visualizador/geógrafo: conservan R de proyectos activos. El contexto sólo selecciona la evidencia aprobada para ese expediente. Si se pretende que esos roles no lean B, hay que aprobar por separado ese cambio de política; no se presenta como parte implícita de SS-05.

No otorgar en un endpoint global la unión de Q(A,D) y Q(B,D) sin contexto: se perdería la separación entre procedencias y podría alterar qué evidencia se muestra como vigente. Un flujo administrativo o comparación explícita puede presentar varios contextos con su autorización propia.

### Vínculos inactivos e histórico (C propuesto, no ejecutado)

| Estado | Admin | Operador sólo A | Operador sólo B | Operador A+B | Visualizador | Geógrafo |
|---|---|---|---|---|---|---|
| LA inactivo, LB activo | Revisión histórica separada; operación ordinaria B | No por LA; no descarga histórica automática | Q(B,D), sin modificación global ordinaria si A sigue protegido | Lectura B; G sólo si cumple todo Pguard o revisión | Sólo contexto B activo | Sólo contexto B activo |
| LB inactivo, LA activo | Revisión y operación A | Q(A,D); G no si B sigue protegido | No por LB | Lectura A; G condicionada | Sólo A activo | Sólo A activo |
| Ambos inactivos | Flujo administrativo de historia, no bypass por rutas ordinarias | No | No | No | No | No |
| V1/V2 anteriores al vínculo de A | Admin puede revisar; publicar exige decisión | Sólo si incluidas expresamente en Q(A,D) | Q(B,D) | Q del contexto | Q del contexto legible | Q del contexto legible |
| V1/V2 anteriores al vínculo de B | Igual | Q(A,D) | Sólo si incluidas en Q(B,D) | Q del contexto | Q del contexto legible | Q del contexto legible |
| Nueva V3 aún no aprobada A/B | Revisión administrativa protegida | No por lista/descarga/consolidado | No | Upload no concede lectura ordinaria si falta aprobación del contexto | No | No |
| Proyecto B inactivo/suspendido | Resolver B por flujo administrativo | Lectura A; G bloqueado mientras B protegido | No lectura ordinaria B | Sin bypass al descartar B de Pguard | Lectura sólo por contexto activo | Igual |
| Un único vínculo abarca A+B | Exigir ámbito declarado/compartición | No retirar ni modificar el vínculo completo sólo por A | Simétrico | Según todos los participantes y dependencias | Q de contexto, sin captura | Igual |

La inactividad de un vínculo deja de conceder acceso ordinario, pero **no borra automáticamente sus obligaciones históricas del conjunto protegido**. La decisión formal de retiro y congelación es distinta de un flag activo.

## Aprobaciones requeridas

D01 granularidad de ámbito; D02 lectura global de roles; D03 promoción y responsables; D04 retroactividad/versiones futuras; D05 escritura global y privados locales; D06 desvinculación/dependencias; D07 baja global/recuperación; D08 proyectos inactivos/retirados; D09 legado; D10 evidencia fijada y estados jurídicos; D11 transición API/UI; D12 revocación/concurrencia y auditoría. Detalle, riesgos y criterios de aceptación en el plan.

**Ninguna celda propuesta se ha implementado o probado como autorización efectiva del producto.** Las 38 comprobaciones puras sólo corroboran la semántica actual; casos integrados pendientes según plan.
