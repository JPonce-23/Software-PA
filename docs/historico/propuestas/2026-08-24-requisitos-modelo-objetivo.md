# Requisitos modelo objetivo - Resumen ejecutivo

> Fecha de alineación: 2026-08-25.

## Requisitos obligatorios

1. Usar Excel local como fuente primaria de campos.
2. Navegar por Proyecto -> Entidad -> Municipio -> Núcleo.
3. Mantener ProyectoNucleo simple.
4. Hacer Parcela central en derechos individuales.
5. Permitir afectación colectiva sin parcela.
6. Normalizar convenios como registros repetibles.
7. Separar RAN del acta y RAN del convenio.
8. Conservar cuatro oficios FIFONAFE.
9. Distinguir indemnización y pago.
10. Usar geometría sólo como apoyo cartográfico.
11. Derivar KPI, trimestres y conteos auxiliares.
12. Preservar observaciones, soporte y excepciones.

## Requisitos negativos

No exigir Tramo, TramoNucleo, usuario_tramo, afectacion_ciclo, intersección espacial, geometría de afectación o `ST_Area` oficial como requisitos del modelo objetivo.

## Requisitos de migración futura

La migración deberá preservar linaje con tipo de convenio, versión/consecutivo, convenio padre, contexto de actividad y relación directa entre afectación, asamblea, convenio, RAN, FIFONAFE y pago.
