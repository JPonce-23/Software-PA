# Descripción canónica del proceso de liberación de derecho de vía

> **Fuente funcional oficial del proyecto.**
> Describe el proceso objetivo aprobado y, cuando es necesario, distingue ese
> objetivo del estado actual de la implementación.

## 1. Principio rector

La jerarquía territorial es:

```text
Proyecto → Tramo → Tramo_Núcleo
```

- `proyecto` agrupa los tramos de una obra ferroviaria.
- `tramo` es la unidad territorial utilizada para asignar responsables y
  medir avance.
- `tramo_nucleo` representa el cruce territorial y administrativo entre un
  tramo y un núcleo agrario y constituye el expediente maestro territorial de
  su liberación de derecho de vía.
- `afectacion` representa un derecho y una superficie confirmados y constituye
  un subexpediente operativo colectivo o individual dentro de ese expediente
  maestro.

Por tanto:

```text
tramo_nucleo = expediente maestro territorial de liberación
afectacion   = subexpediente operativo confirmado
```

Una afectación no sustituye a Proyecto, Tramo o Tramo_Núcleo. Es el registro
que abre una rama operativa dentro del expediente maestro cuando el
caminamiento y el análisis territorial y jurídico ya confirmaron el derecho
afectado, su superficie, geometría y sujetos involucrados.

Antes de esa confirmación, las posibles afectaciones se investigan dentro del
contexto de `tramo_nucleo`. La sensibilización y el caminamiento ocurren en esa
etapa del expediente maestro y no crean subexpedientes preliminares. Cuando se
registra una afectación confirmada, las actuaciones compartidas permanecen en
`tramo_nucleo` y deben ser visibles desde el subexpediente como antecedentes;
las actuaciones exclusivas se relacionan con la afectación correspondiente.

## 2. Secuencia general

```text
Configuración territorial
        ↓
Identificación territorial de posibles afectaciones
        ↓
Acercamiento y sensibilización
        ↓
Caminamiento y análisis territorial y jurídico
        ↓
Confirmación de superficie, geometría, sujetos y BDT
        ↓
Registro de la afectación y apertura del subexpediente operativo
        ↓
Clasificación de la ruta aplicable
    ├── Expropiación directa
    │       └── Salida terminal fuera del seguimiento de la PA
    ├── Comunidad indígena
    │       └── Salida terminal fuera del seguimiento de la PA
    └── Ruta ordinaria colectiva o individual
                ↓
      Firma del convenio
                ↓
      Consolidación y seguimiento registral ante el RAN
                ↓
      FIFONAFE, pago de indemnización y cierre
                ↓
             Liberado
```

La sensibilización no se elimina ni se reemplaza por el caminamiento. Es una
etapa social previa. El caminamiento es una actividad técnica de campo.

La secuencia anterior expresa el orden obligatorio de las etapas aplicables.
Una actuación posterior no sustituye ni presume cumplidas las anteriores.
Expropiación directa y comunidad indígena son salidas terminales: se conserva
su clasificación y evidencia, pero el sistema de la PA no continúa el flujo
ordinario de convenio, RAN, FIFONAFE y pago.

La navegación para el usuario final conserva una jerarquía más directa:

```text
Proyecto
└── Tramo
    └── Tramo_Núcleo
        ├── Expediente maestro territorial
        └── Afectación confirmada
            └── Subexpediente operativo
```

El usuario entra al expediente maestro del cruce, consulta sus antecedentes y
registra las afectaciones con datos confirmados. Desde ahí abre cada
subexpediente colectivo o individual. En éste puede consultar los antecedentes
compartidos que le aplican, además de sus actuaciones posteriores.

## 3. Fase 1 — Configuración e investigación territorial

### 3.1 Proyecto, tramo y núcleo

La Procuraduría Agraria registra o selecciona:

- Proyecto.
- Tramo.
- Núcleo agrario.
- Entidad federativa y municipio de adscripción registral.
- Residencia u oficina regional responsable.
- Tipo de núcleo: ejido o comunidad.
- Cruce `tramo_nucleo`, con consecutivo, longitud y geometría.
- Condiciones especiales: comunidad indígena, expropiación o proyecto que no
  afecta tierras de uso común.

La asignación de usuarios se realiza por tramo mediante `usuario_tramo`. El
modelo vigente no utiliza Frente.

La condición especial debe registrarse en el nivel al que realmente aplica:

- `nucleo_agrario` cuando la condición corresponde al núcleo completo.
- `tramo_nucleo` cuando corresponde a todo el cruce territorial.
- `afectacion` cuando sólo una afectación colectiva o una parcela
  individualizada sale del flujo ordinario.

Una afectación marcada para expropiación directa o por comunidad indígena
conserva sus antecedentes, observaciones, documentos y trazabilidad, pero no
continúa hacia convenio, RAN, FIFONAFE ni pago dentro del sistema de la PA. La
salida no equivale a liberación ni a un problema pendiente.

Cuando el proyecto no afecta tierras de uso común, no se abre la ruta
colectiva. Esto no impide continuar con afectaciones individuales sobre
parcelas cuando existan.

### 3.2 Identificación de posibles afectaciones

El cruce `tramo_nucleo` permite investigar si el proyecto afecta derechos
colectivos o parcelas individualizadas. En esta etapa se reúnen antecedentes,
se revisan las condiciones del núcleo y se programan las actuaciones de campo.

Una posible afectación todavía no es una fila de `afectacion` ni un
subexpediente operativo.
Si el análisis posterior concluye que no existe afectación, las actuaciones
territoriales permanecen como evidencia del expediente maestro sin crear un
subexpediente operativo inexistente.

### 3.3 Identidad y representación

Las personas se registran una sola vez en el catálogo `persona`. Su relación
con un núcleo y su calidad agraria se registra en `persona_nucleo`.

```text
persona
├── persona_nucleo
├── parcela_titular
└── orv_integrante
```

- `parcela_titular` permite titular, cotitulares o posesionarios.
- `orv_integrante` asigna los cargos del Comisariado y Consejo de Vigilancia.
- ORV pertenece al núcleo, no a una afectación particular, porque puede
  respaldar varias actuaciones mientras se encuentre vigente.
- El padrón registra su fecha y número de ejidatarios o comuneros para apoyar
  el cálculo del quórum.

No se fusionan identidades únicamente porque coincida el nombre. CURP válida,
RFC, documentos, núcleo, parcela y vigencia son evidencia para una
conciliación.

## 4. Fase 2 — Acercamiento, sensibilización y caminamiento

### 4.1 Acercamiento y sensibilización

La PA y las instituciones participantes informan al núcleo o a los titulares:

- Alcance y ubicación aproximada del proyecto.
- Motivo de la ocupación.
- Derechos de las personas afectadas.
- Proceso de levantamiento y valuación.
- Documentación requerida.
- Próximas reuniones, recorridos o asambleas.
- Mecanismo de negociación de la tierra y de los BDT.

La sensibilización puede necesitar varias reuniones. Cada actividad debe
registrar como mínimo:

- Fecha programada y realizada.
- Lugar.
- Responsable.
- Resultado y observaciones.
- Acuerdos y próxima acción.
- Evidencia documental.

Las minutas conservan los acuerdos. Cada acuerdo tiene un responsable y puede
registrar prioridad, fecha límite, estatus y fecha de cumplimiento.

Una lista estructurada de participantes por actividad es una capacidad
planeada; no debe asumirse implementada mientras no exista su modelo.

### 4.2 Caminamiento

El caminamiento es la inspección física con representantes, titulares y
personal técnico. Permite:

- Verificar por dónde cruza el proyecto.
- Delimitar la superficie realmente afectada.
- Confirmar o corregir la geometría.
- Identificar parcelas y sujetos involucrados.
- Detectar desacuerdos o conflictos.
- Identificar bienes distintos a la tierra.

Sus resultados permiten determinar si existe una afectación cierta y reúnen la
información necesaria para crearla por la vía colectiva o individual.

### 4.3 Bienes Distintos a la Tierra

Los BDT son bienes adheridos al terreno cuyo valor es independiente del suelo,
por ejemplo:

- Cultivos y árboles.
- Cercas, corrales y caminos interiores.
- Pozos y sistemas de riego.
- Construcciones.
- Infraestructura eléctrica, hidráulica o productiva.

El caminamiento identifica los bienes; posteriormente se valoran y negocian.
El resultado económico acordado se registra en `convenio.monto_bdt`.

Actualmente no existe un inventario estructurado por cada bien. Si los
usuarios requieren esa trazabilidad, debe diseñarse una entidad de inventario
y valuación vinculada a la afectación.

### 4.4 Registro de la afectación confirmada

La afectación se crea únicamente cuando el caminamiento y el análisis
territorial y jurídico confirmaron el derecho afectado. En ese momento nace su
subexpediente operativo dentro de `tramo_nucleo` y el usuario selecciona su
vía:

```text
afectacion.tipo_afectacion
├── colectivo
└── individual
```

La captura requiere:

- Tramo_Núcleo y núcleo agrario.
- Tipo y subtipo de tenencia.
- Destino de la superficie, cuando corresponda.
- Superficie confirmada.
- Geometría poligonal confirmada.
- Situación jurídica.
- Documentación disponible y faltante.
- Parcela y titulares, cuando sea individual.

Una afectación colectiva corresponde normalmente a tierras de uso común y
requiere actuaciones del núcleo agrario. Una afectación individual corresponde
a una parcela o derecho con uno o varios titulares identificables.

## 5. Fase 3A — Derechos colectivos

Las tierras de uso común pertenecen al núcleo agrario. Su autorización requiere
las actuaciones colectivas y registrales aplicables.

### 5.1 COP original colectivo

El ciclo contempla:

1. Sensibilización y caminamiento.
2. Convocatorias y asamblea de anuencia.
3. Registro del quórum y resultado.
4. Confirmación y captura de la superficie real afectada.
5. Captura independiente del valor de tierra y de BDT.
6. Conformación del Acta de Asamblea y firma del Convenio de Ocupación Previa.
7. Consolidación y gestión del acta y del COP.
8. Ingreso y seguimiento ante el RAN del Acta de Asamblea y del COP colectivo.
9. Obtención del aviso y verificación de la inscripción.

### 5.2 Variantes colectivas

Los tipos permitidos son:

```text
cop_original
modificatorio
superficie_adicional
obras_complementarias
```

- **Modificatorio:** ajusta el convenio original y conserva su linaje.
- **Superficie adicional:** incorpora nueva superficie y abre un nuevo ciclo
  de sensibilización, caminamiento, asamblea, convenio y seguimiento ante el
  RAN.
- **Obras complementarias:** crea un ciclo relacional independiente con
  sensibilización, caminamiento, nueva asamblea, nuevo convenio y seguimiento
  ante el RAN; no sobrescribe el COP original.

En obras complementarias no se captura `monto_bdt`. El pago corresponde
solamente al valor pactado por la superficie.

No deben recrearse columnas paralelas con sufijos como `_2`. Cada nuevo ciclo
se representa mediante nuevas filas relacionadas. Las actividades y asambleas
del ciclo utilizan su `contexto_proceso`; el convenio utiliza el
`tipo_convenio` correspondiente.

## 6. Fase 3B — Derechos individuales

La afectación individual se vincula con una parcela y al menos un titular
activo. Puede soportar copropiedad mediante varios registros en
`parcela_titular`.

La PA verifica:

- Número o identificación de parcela.
- Certificado parcelario.
- Folio de derechos.
- Constancia de vigencia.
- Titular, cotitulares o posesionarios.
- Superficie y geometría afectadas.

La negociación se realiza directamente con los titulares y no requiere una
asamblea del núcleo para autorizar el convenio individual.

### 6.1 COP original individual

La ruta individual contempla:

1. Confirmación de la parcela, titulares, superficie y situación jurídica.
2. Integración de la documentación disponible y faltante del subexpediente.
3. Firma del Convenio de Ocupación Previa individual.
4. Consolidación y gestión del COP.
5. Ingreso y seguimiento del convenio ante el RAN.
6. Obtención del aviso y verificación de la inscripción.
7. Continuidad hacia FIFONAFE y el pago de indemnización.

La ruta utiliza `afectacion`, `parcela`, `parcela_titular`, `convenio`,
`tramite_fifonafe` y `pago_indemnizacion`. No requiere una asamblea de anuencia.

### 6.2 Variantes individuales

Los tipos permitidos son:

```text
cop_original
modificatorio
ampliacion
ampliacion_remanente
```

- **COP original:** registra firma, superficie, valor de tierra, BDT y
  seguimiento registral.
- **Modificatorio individual:** ajusta fecha y montos; no registra nueva
  superficie ni BDT y no requiere inscripción ante el RAN conforme a la regla
  actualmente modelada.
- **Ampliación y ampliación remanente:** registran la nueva superficie,
  montos y seguimiento registral correspondiente.

## 7. Fase 4 — FIFONAFE, pagos y cierre

### 7.1 Informe de no conflictos

Se conserva la cadena de oficios entre FIFONAFE, DGAOPR y la representación de
la PA:

- Oficio de FIFONAFE a DGAOPR o representación y fecha.
- Oficio de DGAOPR a representación y fecha.
- Respuesta de la representación a DGAOPR y fecha.
- Respuesta final a FIFONAFE y fecha.

El objetivo es acreditar que existen condiciones para continuar con el pago.

### 7.2 Paquete económico

El paquete de indemnización tiene conceptos complementarios:

```text
valor de la tierra       = convenio.monto_100
anticipo de la tierra    = convenio.monto_90
bienes distintos tierra = convenio.monto_bdt
límite pagable           = monto_100 + monto_bdt
```

`monto_90` es un anticipo incluido dentro de `monto_100`; no se suma como un
tercer concepto.

Reglas por convenio:

- COP original colectivo o individual: `monto_100` y `monto_bdt` se capturan
  de forma independiente, aunque BDT pueda valer cero.
- Ampliaciones: aplican ambos conceptos.
- Obras complementarias: BDT no aplica y debe ser nulo.
- Modificatorio individual: no captura BDT.

### 7.3 Pagos

Cada pago de indemnización se relaciona con un trámite FIFONAFE de tipo
`indemnizacion`, que a su vez debe tener un convenio.

Se registra:

- Monto y fecha.
- Tipo: anticipo, parcial o total.
- Medio de pago.
- Banco y referencia.
- Persona beneficiaria o beneficiario externo.

La suma de pagos activos no puede exceder `monto_100 + monto_bdt`. Tampoco
pueden reducirse los montos del convenio por debajo de lo ya pagado.

Para derechos individuales el pago se dirige al titular o beneficiario
correspondiente. Para derechos colectivos el proceso incluye el depósito y la
asamblea de retiro de fondos cuando proceda.

### 7.4 Liberación y salidas terminales

Para el flujo ordinario descrito en el flujograma de propiedad social, una
afectación se considera liberada cuando concluyeron las etapas que le resultan
aplicables:

```text
Convenio firmado
        ↓
Consolidación y seguimiento ante el RAN
        ↓
Aviso y verificación de inscripción
        ↓
Informe de no conflictos
        ↓
Pago de indemnización concluido
        ↓
Liberado
```

Los hitos intermedios deben conservarse de forma independiente:

- `convenio.fecha_firma`: convenio firmado.
- `convenio.ingreso_ran_fecha`: convenio ingresado al RAN.
- `convenio.calificacion_registral`: resultado del seguimiento registral.
- `convenio.convenio_inscrito_fecha_ran`: inscripción registrada.
- `tramite_fifonafe`: informe de no conflictos e indemnización.
- `pago_indemnizacion`: resultado financiero.

El estado no sustituye esos datos ni se captura como una afirmación aislada; se
calcula a partir de los hitos aplicables. Un `tramo_nucleo` sólo puede
considerarse liberado cuando todas sus afectaciones activas están liberadas.
Cuando combina afectaciones liberadas con salidas terminales debe reportarse
como un expediente mixto, sin ocultar las afectaciones que quedaron fuera del
seguimiento.

Las afectaciones con salida por expropiación directa o comunidad indígena no
son liberadas. Se reportan mediante un estado terminal fuera del seguimiento
de la PA y no continúan acumulando avance ordinario.

## 8. Documentación, alertas y auditoría

- La documentación puede relacionarse con núcleo, afectación, convenio u ORV.
- Cada carga crea una versión inmutable con nombre original, tamaño, MIME,
  SHA-256, usuario y fecha.
- Una nueva versión nunca sobrescribe físicamente la anterior.
- Las alertas de vencimiento de ORV se generan al modificar el ORV y mediante
  una tarea diaria.
- Cada usuario consulta sus alertas no vistas.
- Las altas, modificaciones y bajas lógicas deben conservar actor y
  trazabilidad en bitácora.
- No se realiza borrado físico de entidades operativas.

## 9. Estado actual frente al proceso objetivo

### Implementado

- Proyecto → Tramo → Tramo_Núcleo, sin Frente.
- Personas, relaciones con núcleo, titulares e integrantes ORV.
- Afectaciones colectivas e individuales.
- Actividades de sensibilización y caminamiento.
- Minutas y acuerdos.
- Convenios y variantes.
- Trámite FIFONAFE y pagos.
- Documentos versionados.
- Alertas y scheduler diario.

### Pendiente del Corte principal 2

El frontend ya abre el expediente maestro por `tramo_nucleo`, pero todavía
mezcla dentro de una sola vista todas sus afectaciones:

```text
expediente maestro: /expedientes/:id_tramo_nucleo
subexpediente:      /expedientes/:id_tramo_nucleo/afectaciones/:id_afectacion
```

Se debe:

- Conservar y fortalecer el expediente maestro de `tramo_nucleo`.
- Listar dentro de él sus afectaciones y abrir cada subexpediente.
- Mantener sensibilización, caminamiento y minutas compartidas en el
  expediente maestro y mostrarlas como antecedentes en los subexpedientes a
  los que apliquen.
- Asociar con claridad documentos, convenios, pagos y estados posteriores con
  la afectación correspondiente.
- Mostrar únicamente etapas aplicables a la vía colectiva o individual.
- Mantener ORV como información compartida del núcleo.
- Calcular avance legal, geoespacial y financiero por afectación.
- Aplicar el orden obligatorio entre sensibilización, caminamiento,
  afectación, asamblea cuando corresponda, convenio, RAN, FIFONAFE y pago.
- Calcular el estado de liberación a partir de los hitos aplicables.
- Detener el flujo ordinario y conservar la trazabilidad cuando una afectación
  salga por expropiación directa o comunidad indígena.
- Corregir el panel documental: debe admitir documentos del expediente maestro
  y documentos propios de una afectación, sin asignarlos todos
  indiscriminadamente a un solo nivel.

### Capacidades que requieren diseño adicional

- Lista estructurada de asistencia por actividad.
- Inventario y valuación detallada de cada BDT.
- Tablero de seguimiento visual de acuerdos.
- Avalúo estructurado con sus datos y documentos propios.

No deben presentarse como terminadas hasta contar con modelo, API, interfaz y
pruebas.

## 10. Conceptos fundamentales

- **Núcleo agrario:** ejido o comunidad con personalidad jurídica y patrimonio
  propio.
- **ORV:** órganos de representación y vigilancia del núcleo.
- **Asamblea:** órgano colectivo que autoriza las actuaciones que legalmente le
  corresponden.
- **Sujeto agrario:** persona con una calidad contextual como ejidatario,
  comunero, avecindado o posesionario.
- **Tierras de uso común:** superficie de aprovechamiento colectivo.
- **Parcela:** superficie con derechos individualizados o compartidos.
- **COP:** Convenio de Ocupación Previa.
- **RAN:** Registro Agrario Nacional.
- **FIFONAFE:** institución que interviene en la administración y dispersión de
  recursos conforme al tipo de afectación.
- **BDT:** Bienes Distintos a la Tierra.

El contexto jurídico ampliado se conserva en:

- `docs/Introducción agraria básica.md`.
- `docs/CONVENIOS DE OCUPACIÓN PREVIA.md`.
- `docs/Conceptos.md`.

Las reglas legales deben ser confirmadas por el área jurídica cuando cambie la
normativa o antes de un despliegue con datos reales.
