# Flujo de liberación de derecho de vía en propiedad social

> **Fuente operativa principal:** `flujograma propiedad social.pdf`,
> “Procedimiento general simplificado de liberación en propiedad social”.
>
> Este documento describe únicamente el ámbito de propiedad social y se
> concentra en las actividades donde interviene la Procuraduría Agraria,
> identificadas con pin verde en el flujograma.

## 1. Alcance

La Procuraduría Agraria interviene en la liberación de derechos sobre
propiedad social:

```text
Propiedad social
├── Derechos colectivos
│   └── Tierras de uso común
└── Derechos individuales
    └── Parcelas con derechos individualizados dentro del núcleo agrario
```

Una afectación individual parcelaria no equivale a propiedad privada. Los
predios privados externos al núcleo agrario no forman parte del flujo descrito
en este documento.

El flujograma contiene actuaciones de PA, RAN, SEDATU y FIFONAFE. Los pasos sin
pin verde sólo se mencionan cuando son necesarios para comprender una entrada,
decisión o salida de una actividad de la PA.

## 2. Vista general

```text
Investigación
└── Identificación preliminar del núcleo y las afectaciones
        ↓
Acercamiento y sensibilización
        ↓
Caminamiento
        ↓
Análisis de afectaciones, predios y situación jurídica
        ↓
Registro de la afectación confirmada y apertura de su subexpediente
        ↓
Avalúo externo
        ↓
Negociación
├── Derechos colectivos
│   ├── Convocatorias y asamblea
│   ├── Anuencia o conciliación
│   └── Acta y COP colectivo
└── Derechos individuales
    ├── Asesoría al titular
    ├── Integración del expediente
    └── COP individual
        ↓
Consolidación y gestión de COP
        ↓
Ingreso y seguimiento ante el RAN
        ↓
Verificación de no conflictos
        ↓
Autorización externa y pago por FIFONAFE
```

## 3. Investigación

### 3.1 Identificación de núcleos agrarios

La PA participa con RAN y SEDATU en la identificación de núcleos agrarios que
podrían resultar afectados por el trazo ferroviario.

Resultado esperado:

- Núcleo agrario identificado.
- Cruce territorial localizado.
- Posible afectación reconocida para investigación.

### 3.2 Análisis preliminar de afectaciones

La PA interviene en la revisión preliminar de las posibles afectaciones. En
esta etapa los datos están sujetos a confirmación durante el caminamiento y
todavía no se crea una fila de `afectacion`.

El sistema conserva esta investigación en el contexto territorial de
`tramo_nucleo`, que constituye el expediente maestro territorial de la
liberación. La posible afectación sólo se convierte en subexpediente después
de confirmar superficie, geometría, clasificación y sujetos. Una vez creado,
la sensibilización, el caminamiento y el análisis compartidos deben mostrarse
como antecedentes de esa afectación sin dejar de pertenecer al expediente
maestro.

### 3.3 Condiciones del núcleo

La PA revisa, junto con las instituciones correspondientes:

- Condiciones sociales.
- Situación jurídica.
- Información registral.
- Estatus del padrón.
- Vigencia y situación del ORV.
- Posibles conflictos o impedimentos.

Esta revisión determina con quién debe realizarse el acercamiento y si la
representación del núcleo cuenta con condiciones para continuar.

## 4. Acercamiento, sensibilización y caminamiento

### 4.1 Acercamiento inicial

La PA realiza o participa en el contacto inicial con el núcleo agrario y sus
representantes.

Objetivos:

- Establecer comunicación formal.
- Identificar interlocutores.
- Preparar la reunión de sensibilización.
- Detectar necesidades de asesoría o documentación.

### 4.2 Sensibilización

La PA participa en la reunión de sensibilización con el ORV y los actores
relevantes.

Durante esta actividad:

- Se informa sobre el proyecto y la posible afectación.
- Se explica la intervención institucional.
- Se atienden dudas de los sujetos agrarios.
- Se prepara el caminamiento.
- Se registran observaciones, acuerdos y documentación pendiente.

La sensibilización es una etapa social previa al caminamiento y no debe
omitirse.

### 4.3 Caminamiento

La PA acompaña a RAN, SEDATU, representantes del núcleo y sujetos afectados en
el recorrido de campo.

El caminamiento permite:

- Reconocer físicamente la zona afectada.
- Confirmar los posibles predios o parcelas.
- Recabar observaciones de los afectados.
- Identificar documentación necesaria.
- Preparar el análisis definitivo de las afectaciones.

### 4.4 Análisis de afectaciones

Después del caminamiento, la PA participa en:

- Análisis de las afectaciones identificadas.
- Identificación de predios o parcelas a afectar.
- Revisión de la situación jurídica.
- Confirmación de los sujetos y derechos involucrados.

Cuando el caminamiento y el análisis jurídico confirman la afectación, el
usuario registra `afectacion` con la superficie y geometría definitivas. Ese
registro abre un subexpediente operativo dentro de `tramo_nucleo` y determina
la ruta colectiva o individual. Si no se confirma, no se crea el
subexpediente; el expediente maestro conserva los antecedentes territoriales.

## 5. Dependencia externa: avalúo

El avalúo aparece en el flujograma como insumo previo a la negociación, pero
no tiene pin verde. Por tanto, la PA no es responsable de elaborarlo ni de
determinar el monto.

La PA utiliza el resultado del avalúo para:

- Explicar el proceso a los sujetos agrarios.
- Acompañar la negociación.
- Asesorar durante la asamblea o reunión individual.

El sistema puede registrar el avalúo como antecedente, documento o hito
externo, pero no debe presentarlo como actividad ejecutada por la PA.

## 6. Ruta de derechos colectivos

Esta vía se utiliza cuando la afectación recae sobre derechos colectivos o
tierras de uso común.

### 6.1 Convocatorias y actas de no verificativo

La PA apoya en:

- Emisión de convocatorias.
- Preparación del proceso de asamblea.
- Elaboración de actas de no verificativo cuando corresponda.
- Continuidad hacia una nueva convocatoria.

### 6.2 Asamblea de anuencia

La PA participa en la asamblea donde se presentan:

- El proyecto.
- La superficie afectada.
- El avalúo.
- El proceso expropiatorio.
- La explicación del Convenio de Ocupación Previa.

La función central de la PA es brindar asesoría agraria y acompañamiento a la
asamblea.

### 6.3 Decisión de anuencia

Después de la asamblea se determina si existe anuencia.

```text
¿Existe anuencia?
├── Sí → Acta de Asamblea y firma del COP colectivo
└── No → Conciliación y replanteamiento del proyecto
```

### 6.4 Conciliación y replanteamiento

Cuando no existe anuencia, la PA participa con las demás instituciones en la
conciliación y el replanteamiento del proyecto.

```text
¿Existe acuerdo después de la conciliación?
├── Sí → Retomar Acta de Asamblea y firma del COP
└── No → Valoración externa de expropiación directa
```

La valoración de expropiación directa aparece sin pin verde. El flujograma no
identifica a la PA como participante de esa valoración y el sistema no debe
modelarla como una actividad ejecutada por la PA.

### 6.5 Acta y firma del COP colectivo

Cuando existe anuencia o acuerdo, la PA:

- Apoya y asesora en la conformación del Acta de Asamblea.
- Acompaña la firma del COP colectivo.

## 7. Ruta de derechos individuales en propiedad social

Esta vía corresponde a parcelas con derechos individualizados dentro del
núcleo agrario.

### 7.1 Asesoría sobre el proceso y el COP

La PA brinda al titular:

- Asesoría sobre el proceso expropiatorio.
- Explicación del Convenio de Ocupación Previa.
- Orientación sobre derechos y documentación.

### 7.2 Integración del expediente

La PA acompaña la integración del expediente individual. La documentación
agraria del titular y de la parcela forma parte de ese expediente.

### 7.3 Firma del COP individual

La PA acompaña la firma del COP individual entre las partes correspondientes.
La firma no requiere una asamblea de anuencia del núcleo porque el derecho
está individualizado.

## 8. Consolidación y gestión de los COP

Después de la firma, la PA interviene en la consolidación y gestión de los
COP, tanto colectivos como individuales.

### 8.1 Derechos colectivos

La PA participa en el seguimiento de:

- Ingreso al RAN del Acta de Asamblea y del COP colectivo.
- Obtención del Aviso de Inscripción emitido por el RAN.
- Verificación de la inscripción.

### 8.2 Derechos individuales

La PA participa en el seguimiento de:

- Ingreso al RAN de los COP individuales.
- Obtención del Aviso de Inscripción emitido por el RAN.
- Verificación de la inscripción.

El RAN es responsable de emitir el aviso y realizar la inscripción. La
intervención de la PA corresponde al acompañamiento, gestión y verificación.

## 9. Expediente para pago y FIFONAFE

### 9.1 Integración del expediente para pago

El flujograma muestra la integración de expedientes para el pago como una
actividad sin pin verde. La PA no aparece como responsable de esa integración
y el sistema no debe asignársela como tarea propia.

El resultado es un expediente disponible para continuar con la solicitud de
información y la verificación previa al pago.

### 9.2 Fondos comunes

Para derechos colectivos, la PA brinda asesoría y acompañamiento a los sujetos
agrarios en el proceso de pago de fondos comunes.

### 9.3 Solicitud de información de FIFONAFE

La PA interviene cuando recibe la solicitud de información para el pago de
indemnización por parte de FIFONAFE.

### 9.4 Verificación de no conflictos

La PA:

- Verifica la información del expediente.
- Revisa el estado social y jurídico del núcleo.
- Determina si existen conflictos que impidan continuar.
- Conserva evidencia de la revisión.

### 9.5 Respuesta a FIFONAFE

La PA emite la respuesta sobre la existencia o inexistencia de conflictos para
que FIFONAFE determine si procede el pago.

### 9.6 Pago de indemnización

El pago aparece en el flujograma únicamente con pin de FIFONAFE. Por tanto:

- FIFONAFE ejecuta el pago.
- La PA no debe registrarse como emisora o ejecutora del pago.
- El sistema de la PA puede registrar el resultado, fecha, monto, referencia y
  evidencia para fines de seguimiento y trazabilidad.

## 10. Responsabilidades externas que no deben atribuirse a la PA

Aunque condicionen el expediente, no son actividades ejecutadas directamente
por la PA:

- Elaboración del avalúo.
- Determinación del monto por superficie.
- Valoración de expropiación directa.
- Emisión del Aviso de Inscripción.
- Inscripción registral realizada por el RAN.
- Integración exclusiva del expediente para pago.
- Ejecución material del pago de indemnización.

El sistema puede conservar sus resultados como hitos externos sin convertirlos
en tareas propias de la Procuraduría Agraria.

## 11. Traducción al modelo del sistema

```text
Proyecto
└── Tramo
    └── Tramo_Núcleo
        └── Afectación
            ├── colectiva
            └── individual parcelaria
```

- `tramo_nucleo` es el expediente maestro territorial del cruce y de su
  liberación de derecho de vía.
- `afectacion` identifica un subexpediente operativo confirmado, colectivo o
  individual.
- La investigación, sensibilización y caminamiento comienzan y se conservan
  en el expediente maestro de `tramo_nucleo`.
- `afectacion` se crea únicamente después de confirmar superficie, geometría,
  situación jurídica y sujetos.
- La creación de `afectacion` abre el subexpediente operativo; no da origen al
  expediente maestro ni al proceso territorial previo.
- Sensibilización, caminamiento y análisis compartidos permanecen en
  `tramo_nucleo` y deben ser consultables desde los subexpedientes a los que
  apliquen.
- La navegación del usuario permanece como
  `Proyecto → Tramo → Tramo_Núcleo → Afectación`.
- La clasificación colectiva o individual determina la ruta aplicable.
- Los hitos externos deben guardar institución responsable y evidencia.
- Una actividad sin pin verde no debe asignarse como responsabilidad propia de
  la PA.

## 12. Regla para futuras interpretaciones

Para definir alcance, pantallas, estados o responsabilidades:

1. Consultar primero `flujograma propiedad social.pdf`.
2. Identificar los pasos con pin verde.
3. Modelar como actividad propia únicamente la intervención de la PA.
4. Registrar las demás actuaciones como dependencias o hitos externos cuando
   sean necesarias para dar continuidad.
5. No incorporar la rama de propiedad privada del flujograma técnico.
