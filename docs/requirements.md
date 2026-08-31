# Requirements - Modelo funcional objetivo SOFTWARE-PA

> Estado: requisitos objetivo implementados en el esquema 035; persisten 6 apariciones de `VALIDACIÓN PA/SICT` clasificadas como `DECISION_FUNCIONAL_REQUERIDA`.
> Fecha de actualización: 2026-08-31.  
> La implementación vigente se detalla en `docs/Arquitectura_Actual.md` y `docs/Diccionario_Datos_SSALFER.md`.

## Alcance

El sistema DEBERÁ digitalizar el seguimiento administrativo de liberación de derecho de vía en propiedad social y producir dashboard, reporteador, captura/consulta estructurada, seguimiento administrativo y visor geoespacial de apoyo.

## Requisitos funcionales

### R1. Fuentes y trazabilidad

El sistema DEBERÁ permitir capturar los campos usados en los Excel locales no versionados y conservar trazabilidad de archivo, hoja, fila, columna y soporte cuando se importe o concilie información.

Los documentos fuente literales y la normativa institucional DEBERÁN usarse como contexto, no como generadores automáticos de módulos no observados en Excel.

### R2. Proyecto y ProyectoNucleo

El sistema DEBERÁ administrar proyectos y relacionarlos con núcleos agrarios mediante `ProyectoNucleo`.

`ProyectoNucleo` DEBERÁ contener como mínimo proyecto, núcleo, residencia, responsable, contacto y observaciones. Las referencias históricas de tramo (consecutivo, clave de tramo, número de tramo) se DEBERÁN conservar mediante `proyecto_nucleo_referencia`, no como columnas directas de `proyecto_nucleo`.

El sistema NO DEBERÁ exigir `Tramo` para navegar, autorizar, crear convenio, crear afectación o calcular KPI.

### R3. Núcleo Agrario, ORV y padrón

El sistema DEBERÁ conservar entidad, municipio, nombre, tipo ejido/comunidad, ORV, vigencia, acta de elección inscrita en RAN, fecha de padrón, número de ejidatarios/comuneros, soporte y observaciones.

### R4. Actividades administrativas

El sistema DEBERÁ registrar sensibilizaciones y caminamientos como hechos de `ProyectoNucleo`, sin exigir afectación ni ciclo, con contexto `general`, `superficie_adicional`, `obras_complementarias` u `otro`, fecha programada, fecha realizada, responsable, resultado, soporte y observaciones. Los campos `POR NA`, `TRIMESTRE` y similares se DEBERÁN derivar en reportes.

### R5. Derechos colectivos

El sistema DEBERÁ permitir afectaciones colectivas sin parcela. DEBERÁ registrar destino de superficie, referencia parcela/solar si existe, superficie preliminar, superficie real afectada, avalúo simple, condiciones especiales, soporte y observaciones.

### R6. Parcela y derechos individuales

El sistema DEBERÁ tratar Parcela como entidad central de la ruta individual. DEBERÁ conservar tipo de parcela, número de parcela, número PPT, titulares, certificado parcelario, folio de derechos, constancia de vigencia, geometría opcional, fuente de geometría, soporte y observaciones.

La geometría de parcela NO DEBERÁ ser obligatoria para el seguimiento individual.

### R7. Afectación

El sistema DEBERÁ registrar afectaciones colectivas e individuales con superficies administrativas capturadas. NO DEBERÁ calcular superficies oficiales desde geometría ni bloquear una afectación por falta de intersección espacial.

### R8. Convenios

El sistema DEBERÁ registrar convenios repetibles por afectación. Tipos colectivos: `cop_original`, `modificatorio`, `superficie_adicional`, `obras_complementarias`. Tipos individuales: `cop_original`, `modificatorio`, `ampliacion`, `ampliacion_remanente`.

Cada convenio DEBERÁ conservar fecha programada de firma, fecha de firma, montos 90/100/BDT cuando existan, superficie propia del instrumento, fecha programada de ingreso RAN, ingreso RAN, número de solicitud, calificación registral, inscripción RAN, soporte y observaciones.

El sistema DEBERÁ permitir excepcionalmente asociar un convenio con más de una afectación sin hacer ese flujo obligatorio.

Permuta NO DEBERÁ ser tipo ordinario de convenio; DEBERÁ conservarse como modalidad especial, descripción u observación del COP original, salvo clasificación posterior como instrumento `otro`.

### R9. Asamblea y RAN

El sistema DEBERÁ separar RAN del Acta y RAN del Convenio. Asamblea DEBERÁ pertenecer a `ProyectoNucleo`, ser exclusivamente colectiva y no tener FK directa a una afectación. Uno o varios convenios colectivos PODRÁN referir la misma asamblea de autorización. Para acta se usará `asamblea.numero_solicitud_ran`; para convenio, `convenio.numero_solicitud_ingreso`.

`tipo_asamblea` y `contexto_proceso` DEBERÁN ser conceptos independientes: el tipo clasifica el acto formal y el contexto identifica el proceso operativo que lo motiva.

### R10. FIFONAFE

El sistema DEBERÁ registrar FIFONAFE por `ProyectoNucleo` y ámbito colectivo/individual. Un trámite PODRÁ cubrir varias afectaciones mediante `tramite_fifonafe_afectacion`, validando el mismo ProyectoNucleo y ámbito, sin duplicar sus oficios ni exigir un convenio propietario.

El sistema DEBERÁ conservar oficio FIFONAFE a DGAOPR/Representación y fecha, oficio DGAOPR a Representación y fecha, respuesta Representación a DGAOPR y fecha, respuesta DGAOPR/Representación a FIFONAFE y fecha, acuse FIFONAFE y fecha, resultado/no conflictos, estatus, soporte y observaciones.

### R11. Indemnización y pago

El sistema DEBERÁ distinguir estatus de indemnización de pago. Indemnización DEBERÁ pertenecer directamente a una afectación, con máximo un registro activo por afectación, sin depender obligatoriamente de FIFONAFE. Indemnización DEBERÁ conservar fecha de entrega del expediente SICT a la Procuraduría Agraria. Pago DEBERÁ pertenecer a indemnización y registrar fecha, monto, beneficiario, referencia/evidencia y observaciones. La cadena canónica será `Pago -> Indemnizacion -> Afectacion -> ProyectoNucleo`.

### R12. Dashboard y reportes

El sistema DEBERÁ derivar KPI desde hechos capturados y NO almacenar manualmente totales derivables. Los agregados de Asamblea, FIFONAFE, Indemnización y Pago DEBERÁN calcularse por separado antes de joins N:M para no duplicar hechos. DEBERÁ poder reproducir el contrato del Excel general: núcleos, sensibilizaciones, caminamientos, asambleas, RAN, COP colectivos, modificatorios, superficie adicional, obras complementarias, retiro de fondos, expropiación directa, parcelas afectadas, COP individuales, ampliaciones, indemnizaciones y superficies capturadas.

### R13. Geoespacial

El sistema DEBERÁ mantener PostgreSQL/PostGIS para trazo ferroviario de proyecto, perímetro de núcleo y geometría opcional de parcela. El visor DEBERÁ permitir mapa, visualización, navegación, selección y consulta territorial. La geometría NO DEBERÁ crear expedientes, afectaciones ni ProyectoNucleo automáticamente.

### R14. Seguridad y auditoría

El sistema DEBERÁ conservar roles, auditoría de cambios, integridad relacional y soporte documental. La autorización vigente DEBERÁ ser por proyecto mediante `usuario_proyecto`; `usuario_tramo` fue retirado y no es requisito funcional.

### R15. Documentos

Los documentos DEBERÁN tener identidad lógica y versiones inmutables. DEBERÁN conservar fecha propia del documento (`fecha_documento`) y número de oficio/folio (`numero_folio`), independientes de la fecha de carga del archivo.

## Requisitos negativos explícitos

El modelo objetivo NO DEBERÁ exigir Proyecto -> Tramo como jerarquía, `Tramo_Nucleo` como expediente maestro, afectación obligatoriamente vinculada a Tramo_Nucleo, geometría obligatoria de afectación, intersección espacial como gate, superficies oficiales calculadas por `ST_Area`, `afectacion_ciclo` como requisito funcional ni autorización obligatoria por `usuario_tramo`.

## Decisiones funcionales pendientes

La auditoría de cobertura del 2026-08-26 no reporta `FALTA_UI`, `FALTA_API`, `FALTA_BACKEND` ni `FALTA_MODELO`. Persisten 6 apariciones del encabezado `VALIDACIÓN PA/SICT` clasificadas como `DECISION_FUNCIONAL_REQUERIDA`: la fuente no define actor, resultado, catálogo ni momento del proceso. No se declaran implementadas ni se les asigna significado hasta que el área dueña lo defina.
