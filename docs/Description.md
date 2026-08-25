# SOFTWARE-PA — Descripción funcional objetivo

> **Estado:** definición funcional objetivo para la refactorización del sistema.  
> **Rama de trabajo:** `feature/backend-logica`.  
> **Fecha de actualización:** 2026-08-24.  
> **Importante:** este documento describe lo que el producto debe representar. La implementación vigente se documenta por separado en `docs/Arquitectura_Actual.md`.

## 1. Propósito

SOFTWARE-PA es un sistema web para digitalizar el seguimiento que la Procuraduría Agraria realiza sobre la liberación de derechos de vía ferroviarios en propiedad social.

El sistema sustituye el seguimiento operativo concentrado históricamente en archivos Excel por información estructurada, auditable y consultable, sin convertir un proceso administrativo relativamente directo en un motor geoespacial o una máquina de estados innecesariamente compleja.

El producto tiene dos componentes principales:

1. **Dashboard / Reporteador**, construido con los datos capturados y actualizados por los usuarios.
2. **Visor geoespacial**, utilizado como apoyo visual para mostrar el trazo ferroviario, los núcleos agrarios y, cuando exista cartografía disponible, las parcelas.

La información oficial de superficies, montos, fechas, estatus, convenios, RAN, FIFONAFE e indemnizaciones proviene de la captura documental/administrativa de los usuarios y de las fuentes institucionales disponibles. La geometría no sustituye esos datos.

## 2. Fuentes funcionales

El modelo objetivo se fundamenta en:

- los archivos Excel de seguimiento utilizados por el área;
- `docs/contexto/estructura_datos_propiedad_social_fuente.md`, para los campos y bloques de información;
- `docs/contexto/flujo_liberacion_propiedad_social_fuente.md`, para el orden y bifurcaciones del proceso;
- la documentación institucional de la Procuraduría Agraria y del Registro Agrario Nacional;
- la Ley Agraria vigente, como apoyo para distinguir tierras de uso común y tierras parceladas.

Los archivos `*_fuente.md` son transcripciones de fuentes originales y **no deben modificarse para hacerlos coincidir con la arquitectura técnica**.

La implementación existente es evidencia del estado actual, pero no prevalece sobre las fuentes funcionales para definir el modelo objetivo.

## 3. Navegación principal

La navegación administrativa objetivo es:

```text
Proyecto
  ↓
Entidad Federativa
  ↓
Municipio
  ↓
Núcleo Agrario
  ├── Datos generales
  ├── ORV
  ├── Padrón
  ├── Sensibilización
  ├── Caminamiento
  ├── Derechos colectivos
  └── Parcelas / Derechos individuales
```

Para derechos individuales:

```text
Proyecto → Entidad → Municipio → Núcleo Agrario → Parcela → Convenios
```

Para derechos colectivos:

```text
Proyecto → Entidad → Municipio → Núcleo Agrario → Afectación colectiva → Asamblea / Convenios
```

`Tramo` deja de ser una entidad funcional necesaria para navegar o ser propietario del expediente. Si una fuente histórica conserva `clave_tramo` o `numero_tramo`, pueden mantenerse como referencias opcionales de procedencia, sin crear por ello una jerarquía funcional basada en tramos.

## 4. Contexto Proyecto–Núcleo

Un núcleo agrario es una entidad maestra agraria y puede participar en más de un proyecto. Por ello, el seguimiento no debe colgar directamente del núcleo sin contexto de proyecto.

El modelo objetivo utiliza una relación mínima **Proyecto–Núcleo** para representar que un núcleo está siendo atendido dentro de un proyecto. Esa relación puede contener datos de seguimiento propios del proyecto, por ejemplo:

- consecutivo de seguimiento;
- residencia u oficina responsable;
- persona organizadora agraria responsable;
- datos de contacto;
- observaciones generales.

No debe convertirse en otra entidad compleja ni contener cálculos espaciales.

## 5. Datos propios del Núcleo Agrario

El Núcleo Agrario conserva información que le pertenece por naturaleza y que puede reutilizarse en distintos procesos:

- entidad federativa y municipio;
- denominación del núcleo;
- tipo de núcleo (ejido/comunidad);
- geometría perimetral cuando exista;
- ORV e integrantes;
- vigencia de ORV;
- inscripción del acta de elección en el RAN;
- historial del padrón de ejidatarios/comuneros;
- personas relacionadas con el núcleo;
- parcelas pertenecientes al núcleo.

Que estos datos se muestren dentro de una pantalla de seguimiento no cambia su propiedad lógica.

## 6. Actuaciones generales del Proyecto–Núcleo

La sensibilización y el caminamiento iniciales pertenecen al seguimiento de un núcleo dentro de un proyecto. Deben conservar, como mínimo, los datos que muestran las fuentes Excel:

- tipo de actividad;
- fecha programada;
- fecha realizada;
- resultado/observaciones;
- responsable;
- soporte documental cuando exista.

Las columnas de Excel utilizadas sólo para evitar doble conteo por núcleo (`PROGRAMADA POR NA`, `REALIZADA POR NA`, etc.) no necesitan persistirse: los reportes deben calcular esos conteos mediante registros estructurados y conteos distintos por núcleo.

## 7. Derechos colectivos

Una afectación colectiva representa una superficie o derecho colectivo del núcleo. No se exige una parcela individual, porque los Excel distinguen tierras de uso común, tierras parceladas y otros destinos.

Ejemplos observados en los archivos de seguimiento incluyen tierras de uso común, superficie a favor del núcleo agrario, parcela escolar, UAIM, canales, derechos de paso y solares.

La ruta objetivo es:

```text
Afectación colectiva
  ↓
Asamblea
  └── Seguimiento RAN del acta
  ↓
Convenio(s)
  ├── COP original
  ├── Modificatorio
  ├── Superficie adicional
  └── Obras complementarias
       ↓
  Seguimiento RAN del convenio
       ↓
  FIFONAFE
       ↓
  Informe de no conflictos
       ↓
  Indemnización / Pago
       ↓
  Retiro de fondos, cuando corresponda
```

El seguimiento RAN del acta de asamblea y el seguimiento RAN del convenio son hechos distintos y no deben fusionarse en un único estado genérico.

## 8. Derechos individuales y Parcela

La Parcela es la entidad operativa central de la ruta individual.

Debe poder representar, como mínimo:

- tipo de parcela;
- número de parcela;
- número de parcela PPT;
- titular, cotitulares o posesionarios;
- constancia de vigencia de derechos;
- certificado parcelario;
- folio de derechos;
- geometría de la parcela cuando exista una fuente cartográfica identificable;
- soporte documental y observaciones.

La ruta objetivo es:

```text
Parcela
  ↓
Afectación individual
  ↓
Convenio(s)
  ├── COP original
  ├── Modificatorio
  ├── Ampliación
  └── Ampliación remanente
       ↓
  Seguimiento RAN
       ↓
  FIFONAFE
       ↓
  Informe de no conflictos
       ↓
  Indemnización / Pago
```

Una parcela puede existir aunque todavía no tenga geometría digital disponible. La ausencia de geometría no debe impedir el seguimiento administrativo o jurídico.

## 9. Convenios

El Convenio es una pieza central del seguimiento y normaliza las columnas repetidas de los Excel.

En lugar de crear columnas independientes para cada variante, se registran filas de convenio con `tipo_convenio` y los campos que correspondan: fecha de firma, monto 90 %, monto 100 %, monto BDT cuando aplique, superficie informada, ingreso al RAN, número de solicitud, calificación registral, fecha de inscripción, soporte documental y observaciones.

Tipos objetivo:

- **Colectivos:** `cop_original`, `modificatorio`, `superficie_adicional`, `obras_complementarias`.
- **Individuales:** `cop_original`, `modificatorio`, `ampliacion`, `ampliacion_remanente`.

## 10. RAN, FIFONAFE e indemnización

El sistema debe conservar íntegramente la información que aparece en los Excel sobre:

- ingreso al RAN;
- número de solicitud;
- calificación registral;
- inscripción de actas;
- inscripción de convenios;
- oficio FIFONAFE → DGAOPR/Representación y fecha;
- oficio DGAOPR → Representación y fecha;
- respuesta Representación → DGAOPR y fecha;
- respuesta DGAOPR/Representación → FIFONAFE y fecha;
- estatus de indemnización;
- pagos efectivamente registrados;
- soporte y observaciones.

No se debe exigir una entidad técnica adicional si esos hechos pueden relacionarse directamente con la afectación, asamblea o convenio que les da origen.

## 11. `afectacion_ciclo`

`afectacion_ciclo` pertenece a la arquitectura actualmente implementada, pero **no forma parte del modelo funcional objetivo salvo que una auditoría de datos demuestre una necesidad que no pueda resolverse mediante relaciones directas entre afectación, actividades, asambleas, convenios, RAN y FIFONAFE**.

Las variantes que actualmente se modelan como ciclos aparecen en los Excel como tipos de convenio y actuaciones asociadas. Por ello, la refactorización debe intentar representar esos hechos sin exponer ni depender de un concepto técnico de “ciclo” para el usuario.

## 12. Visor geoespacial

El modelo cartográfico objetivo es deliberadamente pequeño:

```text
Proyecto
└── Trazo ferroviario (línea)

Núcleo Agrario
└── Perímetro (polígono)

Parcela
└── Geometría opcional (polígono)
```

El mapa puede mostrar y centrar el trazo, mostrar núcleos, resaltar núcleos seleccionados, mostrar parcelas cuando exista geometría y navegar desde una geometría hacia su información administrativa.

La geometría **no** debe utilizarse como fuente autoritativa para crear expedientes o afectaciones, calcular la superficie oficial afectada/liberada, determinar montos o liberación, bloquear registros por falta de intersección ni inferir automáticamente datos que los usuarios deben capturar desde fuentes oficiales.

Las superficies de los reportes provienen de los campos administrativos capturados.

## 13. Dashboard / Reporteador

El dashboard debe reproducir y mejorar los indicadores actualmente consolidados en los Excel, por proyecto y con filtros territoriales:

- total de núcleos agrarios;
- sensibilizaciones programadas/realizadas;
- caminamientos programados/realizados;
- asambleas;
- actas ingresadas e inscritas en RAN;
- convenios colectivos por tipo, firma, ingreso e inscripción;
- parcelas afectadas;
- convenios individuales por tipo, firma, ingreso e inscripción;
- superficies informadas por usuarios;
- indemnizaciones y pagos;
- casos de expropiación directa;
- casos donde no se afectan tierras de uso común;
- casos de comunidad indígena o tratamiento especial, según la decisión funcional aplicable.

Los campos auxiliares de Excel como `TRIMESTRE` deben derivarse de las fechas, no duplicarse en la base de datos.

## 14. Roles

El sistema conserva cuatro perfiles generales:

- **Operador:** captura y actualiza información administrativa, agraria y jurídica.
- **Geógrafo:** administra cartografía de proyecto, núcleos y parcelas sin convertir la cartografía en fuente de verdad administrativa.
- **Visualizador:** consulta dashboard, reportes, expedientes y mapa.
- **Administrador:** configura usuarios, proyectos, catálogos y permisos.

Al retirar `Tramo` del dominio funcional, el control territorial por `usuario_tramo` debe reauditarse. El modelo objetivo favorece permisos por proyecto o por un alcance equivalente, sin predeterminar todavía su implementación final.

## 15. Documentos relacionados

- `docs/contexto/estructura_datos_propiedad_social_fuente.md`
- `docs/contexto/flujo_liberacion_propiedad_social_fuente.md`
- `docs/Descripción proceso.md`
- `docs/propuestas/2026-08-24-refactor-modelo-seguimiento-excel.md`
- `docs/propuestas/2026-08-24-matriz-trazabilidad-excel-modelo.md`
- `docs/propuestas/2026-08-24-requisitos-modelo-objetivo.md`
- `docs/propuestas/2026-08-24-diseno-modelo-objetivo.md`
- `docs/propuestas/2026-08-24-plan-migracion-refactor.md`

## 16. Referencias institucionales de apoyo

- Procuraduría Agraria, Normateca — Lineamientos: https://www.pa.gob.mx/normatecapa/lineamientos.html
- Lineamientos/modelos de Convenios de Ocupación Previa: https://www.pa.gob.mx/normatecapa/lineamientos/lineamientos_en_materia_de_convenios.pdf
- Ley Agraria vigente: https://www.diputados.gob.mx/LeyesBiblio/pdf/LAgra.pdf
- Registro Agrario Nacional — Datos abiertos geoespaciales: https://datos.ran.gob.mx/conjuntoDatosPublico.php

Estas referencias apoyan la interpretación del dominio; no sustituyen las decisiones funcionales que correspondan al área responsable del proyecto.
