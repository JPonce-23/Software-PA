# Requisitos del modelo objetivo simplificado

> **Estado:** requisitos para la refactorización; no describen todavía la implementación vigente.  
> **Fecha:** 2026-08-24.

## R1. Alcance

El sistema debe digitalizar el seguimiento actualmente representado en los Excel colectivos, individuales y de reporte general.

## R2. Navegación

La navegación debe partir de Proyecto → Entidad → Municipio → Núcleo Agrario.

## R3. Proyecto–Núcleo

Debe existir un contexto que relacione un Proyecto con un Núcleo Agrario sin depender de `Tramo`.

## R4. Tramo

No debe ser obligatorio como entidad para expediente, permisos, afectaciones, convenios o dashboard. Las referencias históricas de tramo pueden conservarse como campos opcionales.

## R5. Núcleo Agrario

Debe conservar ORV, padrón, personas, parcelas y geometría perimetral.

## R6. Sensibilización y caminamiento

Deben registrarse como actividades del contexto Proyecto–Núcleo, con fechas programadas/realizadas, responsable, resultado, observaciones y soporte.

## R7. Derechos colectivos

Debe poder existir una afectación colectiva sin parcela individual.

Debe capturar destino, superficie informada, referencias de parcela/solar cuando existan, situación, observaciones y soporte.

## R8. Asamblea

Debe capturar convocatorias, fecha realizada, resultado y seguimiento RAN del Acta.

## R9. Convenios colectivos

Debe soportar COP original, modificatorio, superficie adicional y obras complementarias.

## R10. Parcela

Debe ser la entidad central de la ruta individual y capturar número, PPT, certificado, folio, constancia, titulares y geometría opcional.

## R11. Afectación individual

Debe relacionar el contexto Proyecto–Núcleo con una Parcela y conservar la superficie informada y situación jurídica.

## R12. Convenios individuales

Debe soportar COP original, modificatorio, ampliación y ampliación remanente.

## R13. Convenio normalizado

Los datos repetidos horizontalmente en Excel se deben representar como múltiples filas de `convenio` y no como grupos de columnas duplicadas.

## R14. RAN

Debe distinguir RAN del Acta y RAN del Convenio para colectivos.

Debe conservar ingreso, solicitud, calificación e inscripción.

## R15. FIFONAFE

Debe conservar los cuatro oficios y fechas mostrados en los Excel y permitir resultado/estatus.

## R16. Indemnización

Debe conservar el estatus administrativo de indemnización.

## R17. Pago

Debe registrar pagos como hechos financieros separados de la simple condición de indemnización.

## R18. Soporte documental

Debe permitir asociar documentos y observaciones a núcleo, parcela, actividad, asamblea, afectación, convenio, RAN/FIFONAFE o pago según corresponda.

## R19. Geometría

Debe conservarse PostGIS para:

- trazo de Proyecto;
- perímetro de Núcleo Agrario;
- geometría opcional de Parcela.

## R20. Geometría no autoritativa

La geometría no debe:

- crear expedientes;
- crear afectaciones;
- calcular superficie oficial;
- calcular superficie liberada;
- determinar pagos;
- bloquear flujo por no intersección.

## R21. Superficies

Las superficies oficiales mostradas en Dashboard deben provenir de campos capturados por usuarios/fuentes administrativas.

## R22. Dashboard

Debe reproducir los indicadores del Excel general por Proyecto y permitir filtros por Entidad, Municipio y Núcleo.

## R23. Campos derivados

`TRIMESTRE` y columnas de control `POR NA` deben derivarse de fechas y relaciones, no almacenarse.

## R24. `afectacion_ciclo`

El modelo objetivo no debe requerir `afectacion_ciclo` si convenios y actuaciones pueden preservar todo el linaje sin pérdida.

## R25. Seguridad

Al dejar de usar `Tramo`, se debe reemplazar o reauditar `usuario_tramo`. La autorización debe poder resolverse al menos por Proyecto.

## R26. Migración

La migración debe ser no destructiva y seguir EXPAND → MIGRATE → SWITCH → CONTRACT.

## R27. Compatibilidad de datos

Ninguna fila histórica de afectación, asamblea, convenio, FIFONAFE o pago puede perderse al retirar `TramoNucleo` o `AfectacionCiclo`.

## R28. Auditoría

Las altas, modificaciones y bajas de datos críticos deben mantener trazabilidad de usuario y fecha.

## R29. Fuentes cartográficas

La geometría de parcelas sólo se debe cargar cuando exista una fuente identificable. La ausencia de geometría no impide el seguimiento.

## R30. Criterio de aceptación

La refactorización se aprueba cuando:

1. se reproduce la información útil de ambos Excel detallados;
2. se reproducen los KPI del Excel general;
3. no se requieren `TramoNucleo` ni `AfectacionCiclo` en el flujo nuevo;
4. no se calculan superficies oficiales desde geometría;
5. las rutas colectiva e individual permanecen diferenciadas.
