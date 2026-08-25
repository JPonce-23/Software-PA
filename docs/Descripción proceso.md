# Descripción funcional objetivo del proceso de liberación en propiedad social

> **Estado:** modelo funcional objetivo para la refactorización.  
> **Fecha:** 2026-08-24.  
> **Fuentes rectoras:** Excel de seguimiento, `docs/contexto/estructura_datos_propiedad_social_fuente.md` y `docs/contexto/flujo_liberacion_propiedad_social_fuente.md`.  
> **Separación obligatoria:** `docs/Arquitectura_Actual.md` continúa describiendo la implementación vigente hasta que la refactorización sea implementada.

## 1. Principio general

SOFTWARE-PA debe representar los hechos administrativos, agrarios, jurídicos y financieros capturados por los usuarios. La arquitectura técnica debe seguir el proceso real y la estructura de los Excel, no obligar al proceso a adaptarse a entidades técnicas creadas previamente.

El contexto principal de trabajo será un **Núcleo Agrario dentro de un Proyecto**. El Tramo deja de ser dueño del expediente y el trazo ferroviario queda como información cartográfica del proyecto.

## 2. Secuencia general

```text
Proyecto
  ↓
Núcleo Agrario en seguimiento
  ↓
Revisión de ORV y Padrón
  ↓
Sensibilización
  ↓
Caminamiento
  ↓
Identificación de derechos/superficies afectadas
  ├── Derechos colectivos
  │     ↓
  │  Afectación colectiva
  │     ↓
  │  Asamblea
  │     └── RAN del Acta
  │     ↓
  │  Convenio(s)
  │     ↓
  │  RAN del Convenio
  │     ↓
  │  FIFONAFE / No conflictos
  │     ↓
  │  Indemnización / Pago
  │     ↓
  │  Retiro de fondos, cuando aplique
  │
  └── Derechos individuales
        ↓
     Parcela
        ↓
     Afectación individual
        ↓
     Convenio(s)
        ↓
     RAN
        ↓
     FIFONAFE / No conflictos
        ↓
     Indemnización / Pago
```

## 3. Alta del Proyecto y trazo

Cada Proyecto contiene sus datos administrativos y puede tener una geometría lineal de trazo ferroviario.

El trazo se usa para representación cartográfica, orientación y consulta. No se divide obligatoriamente en entidades `Tramo` para efectos del proceso.

Si existen referencias históricas de clave o número de tramo en una fuente Excel, se preservan como datos opcionales de procedencia.

## 4. Núcleo Agrario dentro del Proyecto

Un mismo Núcleo Agrario puede aparecer en más de un proyecto. Por ello se necesita una relación mínima Proyecto–Núcleo para mantener separado el seguimiento de cada proyecto.

En este contexto pueden registrarse:

- consecutivo;
- residencia;
- organizador agrario responsable;
- teléfono/contacto;
- observaciones generales;
- sensibilizaciones;
- caminamientos.

Los datos maestros de ORV, padrón, personas y parcelas continúan perteneciendo al Núcleo Agrario.

## 5. ORV y Padrón

El sistema debe conservar el seguimiento de:

- integrantes/cargos de ORV;
- vigencia;
- fecha de vencimiento;
- inscripción del acta de elección en el RAN;
- fecha de padrón;
- número de ejidatarios/comuneros;
- observaciones y soporte documental.

Estos datos sirven como antecedentes del proceso y para las actuaciones colectivas que corresponda.

## 6. Sensibilización

La sensibilización es una actuación del seguimiento Proyecto–Núcleo.

Debe registrar:

- fecha programada;
- fecha realizada;
- responsable;
- resultado;
- observaciones/acuerdos;
- soporte documental.

Puede haber varias sensibilizaciones. Las columnas Excel `POR NA` no son hechos nuevos y no deben almacenarse como banderas; su función de conteo se resuelve en reportes.

## 7. Caminamiento

El caminamiento es una actividad técnica/administrativa que permite reconocer la superficie o los derechos que serán materia del seguimiento.

Debe registrar:

- fecha programada;
- fecha realizada;
- responsable;
- resultado;
- observaciones;
- soporte documental.

La geometría puede apoyar la visualización del recorrido o de las parcelas, pero la superficie oficial informada se captura desde la documentación administrativa.

## 8. Derechos colectivos

Una Afectación Colectiva representa un derecho o superficie colectiva del núcleo.

Puede corresponder, entre otros, a tierras de uso común, superficies a favor del núcleo, parcela escolar, UAIM, canal, derecho de paso u otros destinos colectivos observados en los Excel.

Campos mínimos:

- destino de la superficie;
- número de parcela/solar cuando exista;
- superficie preliminar cuando sea relevante;
- superficie real afectada informada;
- situación/observaciones;
- soporte documental.

### 8.1 Asamblea

La Asamblea debe conservar:

- primera convocatoria;
- segunda convocatoria;
- fecha realizada;
- resultado;
- ingreso al RAN;
- número de solicitud;
- calificación registral;
- inscripción del acta;
- soporte y observaciones.

Las variantes de asamblea deben conservarse cuando aparecen en la fuente, incluyendo anuencia, no verificativo, conciliación y retiro de fondos, según aplique.

### 8.2 Convenios colectivos

Tipos:

- COP original;
- modificatorio;
- superficie adicional;
- obras complementarias.

Cada Convenio registra sus propios datos económicos, de superficie y registrales.

Una superficie adicional u obra complementaria puede requerir nuevas actuaciones (sensibilización, caminamiento o asamblea). Esas actuaciones deben relacionarse con el convenio/afectación correspondiente sin obligar al usuario a crear o comprender una entidad `afectacion_ciclo`.

## 9. Derechos individuales

La ruta individual se organiza por Parcela.

### 9.1 Parcela

Campos mínimos:

- tipo;
- número de parcela;
- número de parcela PPT;
- certificado parcelario;
- folio de derechos;
- constancia de vigencia;
- titular(es), cotitulares o posesionarios;
- geometría opcional;
- soporte y observaciones.

La geometría de la parcela es opcional y puede cargarse cuando exista una fuente cartográfica confiable.

### 9.2 Afectación individual

Representa la afectación del Proyecto sobre la Parcela dentro del contexto Proyecto–Núcleo.

Conserva la superficie oficial informada, situación jurídica y observaciones. No requiere que PostGIS calcule esa superficie.

### 9.3 Convenios individuales

Tipos:

- COP original;
- modificatorio;
- ampliación;
- ampliación remanente.

Cada convenio conserva firma, montos, BDT cuando corresponda, superficie, RAN, soporte y observaciones.

## 10. RAN

Hay al menos dos seguimientos registrales que deben distinguirse en derechos colectivos:

1. RAN del Acta de Asamblea.
2. RAN del Convenio.

Para Convenios individuales se registra el seguimiento RAN del propio convenio.

Campos recurrentes:

- fecha de ingreso;
- número de solicitud;
- calificación registral;
- fecha de inscripción/aviso;
- soporte documental;
- observaciones.

## 11. FIFONAFE e Informe de No Conflictos

Se conservan los cuatro oficios observados en las fuentes:

1. FIFONAFE → DGAOPR/Representación y fecha.
2. DGAOPR → Representación y fecha.
3. Respuesta Representación → DGAOPR y fecha.
4. Respuesta DGAOPR/Representación → FIFONAFE y fecha.

El sistema puede registrar además el resultado del informe, el estatus y observaciones.

## 12. Indemnización y pago

El Excel conserva un estatus de indemnización y el sistema actual ya cuenta con pagos. En el modelo objetivo deben distinguirse:

- **estatus de indemnización**: programado, pendiente, completo u otro catálogo aprobado;
- **pago**: hecho financiero registrado con fecha, monto, beneficiario y evidencia cuando aplique.

El Dashboard no debe inferir un pago a partir de geometría.

## 13. Expropiación directa, comunidad indígena y no afectación de uso común

Los Excel contienen expresamente estas condiciones y deben preservarse.

Sin embargo, el efecto exacto sobre el flujo debe mantenerse como decisión funcional auditable. En particular:

- `no afecta tierras de uso común` debe impedir o excluir la ruta colectiva cuando corresponda, sin eliminar automáticamente una posible ruta individual;
- `expropiación directa` debe conservarse como condición/resultado del caso;
- `comunidad indígena` debe registrarse y permitir el tratamiento específico que el área determine.

No se debe convertir una clasificación del Excel en una salida terminal global si la fuente funcional no lo justifica para todas las rutas.

## 14. `afectacion_ciclo`

El concepto `afectacion_ciclo` fue introducido por la implementación para agrupar COP original y variantes posteriores.

El modelo objetivo no lo necesita como concepto de usuario. Antes de retirarlo se debe verificar que:

- cada convenio conserva su tipo y linaje;
- las actuaciones adicionales pueden asociarse al convenio/afectación;
- asambleas, RAN, FIFONAFE y pagos pueden relacionarse sin pérdida;
- la migración preserva todos los registros históricos.

Si esas condiciones se cumplen, `afectacion_ciclo` se retira en la fase CONTRACT.

## 15. Geoespacial

Sólo se necesitan como capacidades centrales:

- trazo ferroviario por Proyecto;
- perímetro de Núcleo Agrario;
- geometría opcional de Parcela.

La geometría se usa para mapa y navegación. No calcula ni sustituye:

- superficie oficial afectada;
- superficie liberada;
- existencia de afectación;
- monto de convenio;
- estado RAN;
- FIFONAFE;
- pago.

## 16. Dashboard

El Dashboard deriva sus indicadores de los hechos capturados.

Debe poder reproducir los bloques del Excel general: núcleos, sensibilización, caminamiento, asambleas, RAN, convenios por tipo, parcelas, ampliaciones, expropiaciones, retiro de fondos, indemnizaciones y superficies informadas.

Los periodos como trimestre se calculan desde las fechas.

## 17. Referencias

- `docs/contexto/flujo_liberacion_propiedad_social_fuente.md`
- `docs/contexto/estructura_datos_propiedad_social_fuente.md`
- Procuraduría Agraria, Normateca: https://www.pa.gob.mx/normatecapa/lineamientos.html
- Lineamientos/modelos de COP: https://www.pa.gob.mx/normatecapa/lineamientos/lineamientos_en_materia_de_convenios.pdf
- Ley Agraria: https://www.diputados.gob.mx/LeyesBiblio/pdf/LAgra.pdf
- RAN, datos abiertos: https://datos.ran.gob.mx/conjuntoDatosPublico.php
