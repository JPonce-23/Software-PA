# SOFTWARE-PA - Descripción funcional objetivo

> Estado: modelo funcional objetivo aprobado para diseño de migración.  
> Fecha de actualización: 2026-08-25.  
> Rama de referencia: `feature/backend-logica`.  
> Este documento describe el producto objetivo; `docs/Arquitectura_Actual.md` y `docs/Diccionario_Datos_SSALFER.md` siguen describiendo la implementación vigente.

## Propósito

SOFTWARE-PA digitaliza y estructura el seguimiento que hoy se concentra en archivos Excel de la Procuraduría Agraria. Su objetivo principal es producir captura estructurada, consulta, seguimiento administrativo, dashboard/reporteador y un visor geoespacial de apoyo.

El sistema no debe convertirse en un GIS complejo ni en una máquina de estados innecesaria. La geometría ayuda a visualizar, seleccionar, resaltar y consultar territorio, pero no crea expedientes ni determina superficies, liberación, indemnización o pago.

## Fuentes y precedencia

Los tres Excel locales se verificaron el 2026-08-25 en `fuentes_locales/excel/`; pudieron abrirse como libros OOXML y se listaron sus hojas. `fuentes_locales/` está excluido en `.gitignore`, por lo que estas fuentes no deben versionarse ni copiarse dentro de directorios de Git.

La documentación institucional se usa sólo para interpretar el dominio: Reglamento de la Ley Agraria en Materia de Ordenamiento de la Propiedad Rural, artículos 56 y 57; Lineamientos en Materia de Convenios de Ocupación Previa y Expropiación de Tierras Ejidales o Comunales de la Procuraduría Agraria; y fuentes oficiales del RAN para núcleos, parcelas/cartografía y trámites registrales. Ninguna de estas fuentes sustituye los campos realmente usados en el seguimiento Excel.

Las fuentes literales versionadas `docs/contexto/estructura_datos_propiedad_social_fuente.md` y `docs/contexto/flujo_liberacion_propiedad_social_fuente.md` se conservan sin reescritura. El flujograma ayuda a entender significado y orden, pero no crea módulos si los Excel no demandan datos de captura.

## Modelo funcional

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
        │   └── Afectación colectiva
        │       ├── Avalúo simple, cuando exista
        │       ├── Asamblea -> RAN del Acta
        │       └── Convenio(s) -> RAN del Convenio -> FIFONAFE -> Indemnización -> Pago
        └── Derechos individuales
            └── Parcela
                └── Afectación individual
                    └── Convenio(s) -> RAN -> FIFONAFE -> Indemnización -> Pago
```

`Tramo` deja de ser entidad funcional obligatoria. Las columnas `CLAVE DEL TRAMO` y `NÚMERO DE TRAMO`, cuando existan, se conservan sólo como referencias históricas/opcionales en `proyecto_nucleo` o en metadatos de importación.

`ProyectoNucleo` es deliberadamente simple: proyecto, núcleo, consecutivo, residencia, responsable, teléfono/contacto, referencias históricas de tramo y observaciones. No contiene cálculos GIS ni motor de estados.

La navegación administrativa objetivo es `Proyecto -> Entidad Federativa -> Municipio -> Núcleo Agrario`. Dentro del núcleo se muestran Resumen, Datos generales, ORV, Padrón, Sensibilización, Caminamiento, Derechos colectivos y Parcelas/Derechos individuales.

La ruta individual es `Proyecto -> Entidad -> Municipio -> Núcleo -> Parcela -> Convenios`. La ruta colectiva es `Proyecto -> Entidad -> Municipio -> Núcleo -> Afectación colectiva -> Asamblea / Convenios`.

## Derechos colectivos

Una afectación colectiva puede existir sin parcela. Representa tierras de uso común, superficie a favor del núcleo, parcela escolar, UAIM, canal, derecho de paso, solares, infraestructura u otros destinos observados. Conserva destino, superficie preliminar, superficie real afectada, avalúo simple si existe, observaciones y soporte.

El RAN del acta de asamblea y el RAN del convenio son seguimientos distintos. El número de solicitud de acta va a `asamblea.numero_solicitud_ran`; el número de solicitud de convenio va a `convenio.numero_solicitud_ingreso`.

## Derechos individuales

Parcela es la entidad operativa central. Conserva tipo, número, número PPT, titulares, certificado parcelario, folio de derechos, constancia de vigencia, geometría opcional, fuente de geometría, soporte y observaciones. La falta de geometría no impide crear o dar seguimiento a la parcela ni a su afectación.

## Convenios

`convenio` es central y repetible. Los bloques horizontales de Excel se normalizan como filas de convenio.

Tipos ordinarios colectivos: `cop_original`, `modificatorio`, `superficie_adicional`, `obras_complementarias`.

Tipos ordinarios individuales: `cop_original`, `modificatorio`, `ampliacion`, `ampliacion_remanente`.

Permuta no se agrega automáticamente al catálogo ordinario: se representa como `tipo_convenio = cop_original` con `modalidad_especial = permuta`, descripción y observaciones. Si un documento posterior demuestra otro instrumento jurídico, podrá clasificarse como `tipo_instrumento = otro` con descripción libre.

Excepcionalmente un convenio puede asociarse a más de una afectación mediante una relación simple `convenio_afectacion(id_convenio, id_afectacion)`. La experiencia normal sigue siendo crear convenio desde una afectación y sólo asociar otra afectación cuando el caso lo requiera.

## Superficies, avalúo, FIFONAFE y pago

No se colapsan `SUPERFICIE TOTAL PRELIMINAR` y `SUPERFICIE TOTAL REAL AFECTADA`: se documentan como `afectacion.superficie_preliminar_ha` y `afectacion.superficie_afectada_ha`. La superficie propia de un instrumento vive en `convenio.superficie_ha` cuando corresponda.

`AVALÚO MAESTRO (INDAABIN) $` se representa de forma simple como `afectacion.avaluo_monto`; `avaluo_fecha`, `avaluo_referencia` e `avaluo_institucion` pueden quedar nulos, usando `INDAABIN` cuando la fuente lo indique.

FIFONAFE conserva cuatro oficios y fechas: FIFONAFE a DGAOPR/Representación, DGAOPR a Representación, respuesta de Representación a DGAOPR y respuesta DGAOPR/Representación a FIFONAFE, además de resultado/no conflictos, estatus, soporte y observaciones.

Indemnización y pago no son equivalentes. Indemnización conserva estatus; pago registra hechos financieros con fecha, monto, beneficiario, referencia/evidencia y observaciones.

## Geoespacial

PostgreSQL y PostGIS se mantienen para trazo ferroviario por proyecto, perímetro del núcleo y geometría opcional de parcela. La geometría no bloquea capturas administrativas, no calcula superficies oficiales con `ST_Area`, no valida liberación ni crea ProyectoNucleo por intersección.

## Dashboard

El Excel general funciona como contrato de aceptación del dashboard. Los KPI se derivan de hechos capturados: núcleos, sensibilizaciones, caminamientos, asambleas, RAN, COP colectivos, modificatorios, superficie adicional, obras complementarias, retiro de fondos, expropiación directa, parcelas afectadas, COP individuales, ampliaciones, indemnizaciones y superficies capturadas.

Los Excel detallados disponibles validan especialmente Mexico-Queretaro; el Excel general incluye otros proyectos que pueden no tener fuente detallada equivalente disponible localmente.

## Referencias institucionales consultadas

- Reglamento de la Ley Agraria en Materia de Ordenamiento de la Propiedad Rural, especialmente artículos 56 y 57: https://www.diputados.gob.mx/LeyesBiblio/regley/Reg_LAgra_MOPR.pdf
- Procuraduría Agraria, Lineamientos en Materia de Convenios de Ocupación Previa y Expropiación de Tierras Ejidales o Comunales: https://www.pa.gob.mx/normatecapa/lineamientos/lineamientos_en_materia_de_convenios.pdf
- Procuraduría Agraria, Normateca de lineamientos: https://www.pa.gob.mx/normatecapa/lineamientos.html
- Registro Agrario Nacional, Datos Abiertos: https://datos.ran.gob.mx/conjuntoDatosPublico.php
- Registro Agrario Nacional, PHINA: https://phina.ran.gob.mx/
