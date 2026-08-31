# Design - Modelo objetivo SOFTWARE-PA

> Estado: diseño funcional implementado mediante 031-033, aislamiento PostgreSQL mediante 034 y completitud operativa mediante 035.
> Fecha de actualización: 2026-08-31.  
> La arquitectura vigente sigue descrita en `docs/Arquitectura_Actual.md` y `docs/Diccionario_Datos_SSALFER.md`.

## Arquitectura lógica

SOFTWARE-PA mantiene FastAPI, React, PostgreSQL, PostGIS, auditoría, integridad relacional, soporte documental, roles y visor cartográfico. El diseño objetivo cambia el centro del dominio hacia los datos reales del seguimiento Excel.

```text
Proyecto
├── Trazo ferroviario (representación cartográfica)
└── ProyectoNucleo
    └── Núcleo Agrario
        ├── Datos generales
        ├── ORV
        ├── Padrón
        ├── Sensibilización
        ├── Caminamiento
        ├── Derechos colectivos
        │   ├── Asamblea -> RAN del Acta
        │   └── Afectación colectiva
        │       ├── Avalúo simple, cuando exista
        │       ├── Convenio(s) -> RAN del Convenio
        │       ├── FIFONAFE / no conflictos (puede cubrir varias afectaciones)
        │       └── Indemnización -> Pago(s)
        └── Derechos individuales
            └── Parcela
                └── Afectación individual
                    ├── Convenio(s) -> RAN
                    ├── FIFONAFE / no conflictos (puede cubrir varias afectaciones)
                    └── Indemnización -> Pago(s)
```

## Entidades objetivo

### Proyecto

Contiene datos administrativos del proyecto y uno o más trazos ferroviarios para representación cartográfica. El trazo no crea expedientes ni afectaciones.

### ProyectoNucleo

Relaciona Proyecto y Núcleo Agrario. Campos directos: `id_proyecto`, `id_nucleo`, `residencia`, `responsable_nombre`, `contacto`, `observaciones` y metadatos de auditoría.

Las referencias históricas de tramo —consecutivo, clave de tramo y número de tramo— se almacenan mediante `proyecto_nucleo_referencia` (`tipo_referencia` ∈ `consecutivo`, `clave_tramo`, `numero_tramo`, `otro`), con `es_principal` y valor libre; no son columnas directas de `proyecto_nucleo`.

### NucleoAgrario

Conserva entidad, municipio, nombre, tipo, geometría perimetral opcional, comunidad indígena cuando aplique, ORV, padrón y relaciones con parcelas.

### Parcela

Entidad central de individuales: tipo, número, número PPT, titulares, certificado parcelario, folio de derechos, constancia de vigencia, geometría opcional, fuente de geometría, documentos y observaciones.

### Afectacion

Puede ser colectiva o individual. Colectiva no exige parcela. Individual se relaciona con Parcela. Conserva destino, superficies administrativas, avalúo simple, condiciones especiales, observaciones y soporte.

Campos de superficie separados: `superficie_preliminar_ha`, `superficie_afectada_ha`. Campos de avalúo: `avaluo_monto`, `avaluo_fecha`, `avaluo_referencia`, `avaluo_institucion`.

### ActividadCampo

Sensibilización y caminamiento pertenecen a `ProyectoNucleo`, sin FK obligatoria a afectación ni ciclo. `contexto_actividad` distingue `general`, `superficie_adicional`, `obras_complementarias` u `otro`.

### Asamblea

Pertenece a `ProyectoNucleo`, es exclusivamente colectiva y no tiene FK directa a afectación. Conserva tipo, convocatorias, realización, resultado, RAN del acta, soporte y observaciones. Varios convenios colectivos pueden referir una misma asamblea mediante `convenio.id_asamblea_autorizacion` nullable.

`tipo_asamblea` clasifica el acto formal (`anuencia`, `modificatorio`, `superficie_adicional`, `obras_complementarias`, `retiro_fondos`, `otra`). `contexto_proceso` (migración 035, nullable) identifica el proceso operativo que motiva la asamblea sin sustituir al tipo; ambos son conceptos distintos.

### Convenio

Entidad repetible. Campos mínimos: `tipo_convenio`, `tipo_instrumento`, `modalidad_especial`, `descripcion_modalidad`, `consecutivo`, `id_convenio_padre`, fecha programada de firma, fecha de firma, montos, superficie propia, fecha programada de ingreso RAN, ingreso RAN, número de solicitud, calificación registral, inscripción, soporte y observaciones.

Relación excepcional `convenio_afectacion(id_convenio, id_afectacion)` para convenios que cubran más de una superficie/afectación.

### FIFONAFE, indemnización y pago

`tramite_fifonafe` pertenece a `ProyectoNucleo`, distingue ámbito colectivo/individual y se vincula N:M con las afectaciones cubiertas mediante `tramite_fifonafe_afectacion`; no depende de un convenio. Conserva los cuatro oficios, fechas, `acuse_fifonafe_fecha` (migración 035), resultado/no conflictos, estatus, soporte y observaciones.

`indemnizacion` pertenece directamente a una afectación, con máximo un registro activo por afectación. Conserva `fecha_entrega_expediente_pa` (migración 035) para la entrega del expediente SICT a la Procuraduría Agraria. `pago` pertenece a indemnización. La cadena financiera canónica es `Pago -> Indemnizacion -> Afectacion -> ProyectoNucleo`; FIFONAFE es seguimiento relacionado, no su padre obligatorio.

### Documento

Identidad lógica con versiones inmutables (`documento_version`). Conserva tipo, estado, título, descripción, `fecha_documento` y `numero_folio` (migración 035) como metadatos propios del soporte independientes de la fecha de carga.

## Navegación UI

La UI administrativa se organiza por `Proyecto -> Entidad -> Municipio -> Núcleo`. Dentro del núcleo: Resumen, Datos generales, ORV, Padrón, Sensibilización, Caminamiento, Derechos colectivos y Parcelas/Derechos individuales.

La experiencia normal crea convenio desde la afectación. La asociación de otra afectación a un convenio se presenta sólo como acción excepcional.

## Diseño geoespacial

PostGIS se usa para almacenamiento y consulta cartográfica: trazo lineal del proyecto, polígono del núcleo, polígono opcional de parcela, SRID, fuente, fecha de fuente, validación geométrica y procedencia.

No usar `ST_Intersects` como regla de negocio para crear expediente/afectación. No usar `ST_Area` como fuente de superficies oficiales o KPI de liberación. Las áreas calculadas pueden mostrarse como referencia cartográfica, nunca como dato oficial sin confirmación administrativa.

## Dashboard

Las vistas y consultas del dashboard se diseñan sobre hechos capturados. Asamblea se agrega por ProyectoNucleo; FIFONAFE por trámite sin multiplicarlo por sus afectaciones; indemnización por afectación y pago por indemnización. Los agregados se calculan de forma independiente antes de joins N:M. Los totales de Excel se usan como contrato de aceptación y conciliación, no como tabla primaria de totales manuales.

Indicadores mínimos: núcleos, sensibilizaciones, caminamientos, asambleas, ingreso/inscripción RAN de actas y convenios, COP por tipo, superficie adicional, obras complementarias, retiro de fondos, expropiación directa, parcelas afectadas, ampliaciones, indemnizaciones, pagos y superficies capturadas.

## Seguridad

Se mantienen roles y auditoría. El alcance objetivo se define por proyecto mediante `usuario_proyecto`. `usuario_tramo` fue retirado físicamente en la migración 032 y no forma parte del modelo vigente.

## Migración implementada

La migración preserva linaje sin `afectacion_ciclo` mediante tipo de convenio, versión/consecutivo, convenio padre, contexto de actividad, referencias y relaciones directas. `TramoNucleo` y `AfectacionCiclo` no se exponen como piezas del modelo implementado.

## Exclusiones de diseño objetivo

No forman parte del diseño objetivo: `TramoNucleo` como expediente maestro, navegación Proyecto -> Tramo -> TramoNucleo, motor oficial de cálculo de superficies, `ST_Intersects` como gate, `ST_Area` para KPI oficiales, `AfectacionCiclo` como pieza necesaria, `usuario_tramo` como autorización objetivo ni geometría obligatoria de afectación.
