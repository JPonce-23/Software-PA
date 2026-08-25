# Matriz de trazabilidad - Excel -> modelo objetivo

> Fecha de auditoría: 2026-08-25.  
> Fuente primaria: libros Excel locales en `fuentes_locales/excel/`.  
> Estados permitidos: `PERSISTIR`, `DERIVAR`, `REFERENCIA`, `DOCUMENTAR`, `REVISAR`, `NO IMPLEMENTAR`.

## Verificación de libros

| Archivo | Existe | Abre | Hojas |
|---|---:|---:|---|
| `PROYECTOS VÍAS SEGUIMIENTO GENERAL.xlsx` | Sí | Sí | `INFORME GENERAL`, `COP´S COLECTIVOS`, `INDIVIDUALES` |
| `SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS-INDIVIDUALES-MQ.xlsx` | Sí | Sí | `General `, `PROPUESTA`, `COP´S PENDIENTES`, `Hoja2`, `Hoja1` |
| `Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx` | Sí | Sí | `General `, `INFORME M-Q`, `ORV`, `ASAMBLEAS PENDIENTES`, `PCOLECTIVAS` |

## Clasificación de hojas

| Archivo | Hoja | Clasificación | Filas no vacías | Filas de datos estimadas | Observación |
|---|---|---|---:|---:|---|
| `PROYECTOS VÍAS SEGUIMIENTO GENERAL.xlsx` | `INFORME GENERAL` | B. REPORTE / DERIVADO | 45 | 45 | Contrato de aceptación del dashboard general por proyecto y año; no se persisten totales si se pueden derivar. |
| `PROYECTOS VÍAS SEGUIMIENTO GENERAL.xlsx` | `COP´S COLECTIVOS` | B. REPORTE / DERIVADO | 27 | 27 | Resumen de COP colectivos por proyecto, destino y tipo de convenio. |
| `PROYECTOS VÍAS SEGUIMIENTO GENERAL.xlsx` | `INDIVIDUALES` | B. REPORTE / DERIVADO | 35 | 35 | Resumen de COP individuales, parcelas y ampliaciones por proyecto. |
| `SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS-INDIVIDUALES-MQ.xlsx` | `General ` | B. REPORTE / DERIVADO | 21 | 19 | Resumen compacto de ruta individual/colectiva; sirve para contraste, no como tabla nueva. |
| `SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS-INDIVIDUALES-MQ.xlsx` | `PROPUESTA` | A. FUENTE DETALLADA | 779 | 775 | Fuente detallada principal de derechos individuales Mexico-Queretaro. |
| `SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS-INDIVIDUALES-MQ.xlsx` | `COP´S PENDIENTES` | A. FUENTE DETALLADA | 692 | 688 | Fuente detallada filtrada/control de COP pendientes; se concilia contra PROPUESTA para evitar duplicados. |
| `SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS-INDIVIDUALES-MQ.xlsx` | `Hoja2` | D. HISTÓRICO / NO RELEVANTE | 0 | 0 | Hoja vacía en la auditoría local. |
| `SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS-INDIVIDUALES-MQ.xlsx` | `Hoja1` | C. CONTROL AUXILIAR | 38 | 37 | Control auxiliar de COP individuales por núcleo; contiene permuta y convenio para dos solares. |
| `Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx` | `General ` | B. REPORTE / DERIVADO | 21 | 19 | Resumen compacto; no sustituye a INFORME M-Q ni ASAMBLEAS PENDIENTES. |
| `Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx` | `INFORME M-Q` | A. FUENTE DETALLADA | 120 | 115 | Fuente detallada principal de derechos colectivos Mexico-Queretaro. |
| `Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx` | `ORV` | A. FUENTE DETALLADA | 78 | 75 | Fuente detallada de ORV, padron y soporte documental por núcleo. |
| `Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx` | `ASAMBLEAS PENDIENTES` | A. FUENTE DETALLADA | 79 | 75 | Fuente detallada/control de asambleas pendientes y excepciones; se concilia con INFORME M-Q. |
| `Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx` | `PCOLECTIVAS` | C. CONTROL AUXILIAR | 7 | 6 | Control auxiliar de COP colectivos por núcleo; contiene permuta y convenio relacionado con dos solares. |

## Criterios de tratamiento

- Los reportes derivados del Excel general son contrato de aceptación del dashboard; sus totales no se persisten si pueden calcularse desde hechos capturados.
- Las hojas detalladas Mexico-Queretaro son fuente primaria para campos de captura colectiva e individual.
- Las hojas auxiliares se usan para conciliación y excepciones, evitando duplicar totales en base de datos.
- Toda columna con datos reales queda con destino, derivación o preservación documental. Las columnas vacías no justifican módulos nuevos.
- `NO. DE SOLICITUD DE INGRESO` de convenio se mapea a `convenio.numero_solicitud_ingreso`; en actas se mapea a `asamblea.numero_solicitud_ran`.

## `PROYECTOS VÍAS SEGUIMIENTO GENERAL.xlsx` - `INFORME GENERAL`

Clasificación: **B. REPORTE / DERIVADO**. Contrato de aceptación del dashboard general por proyecto y año; no se persisten totales si se pueden derivar.

| Col. | Columna fuente | Filas con dato | Estado | Tipo de tratamiento | Entidad destino | Campo destino | Persiste | Deriva | Referencia | Requiere decisión | Observación |
|---:|---|---:|---|---|---|---|---:|---:|---:|---:|---|
| A | PROYECTO | 39 | DOCUMENTAR | documentar | `dashboard` | `dimension_reporte` | No | Si | No | No | Dimension de reporte; se alimenta desde hechos capturados. |
| B | TOTAL DE NÚCLEOS AGRARIOS | 33 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| C | SENSIBILIZACIÓN / Programado | 24 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| D | Realizado | 21 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| E | CAMINAMIENTO / Programado | 24 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| F | Realizado | 21 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| G | ASAMBLEA DE ANUENCIA Y APROBACIÓN DEL CONVENIO DE OCUPACIÓN PREVIA (COP) / Asambleas / Programado | 27 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| H | Realizado | 27 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| I | Ingreso al RAN / Programado | 24 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| J | Realizado | 21 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| K | Acta Inscrita en el RAN / Programado | 24 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| L | Realizado | 21 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| M | CONVENIO DE OCUPACIÓN PREVIA - INSCRIPCIÓN / Convenio firmado / Programado | 27 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| N | Realizado | 21 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| O | COP Ingreso al RAN / Programado | 24 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| P | Realizado | 21 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| Q | COP Inscrito RAN / Programado | 24 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| R | Realizado | 21 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| S | CONVENIO MODIFICATORIO-INSCRIPCIÓN / Convenio firmado / Programado | 27 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| T | Realizado | 27 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| U | CONVENIO Ingreso al RAN / Programado | 24 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| V | Realizado | 21 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| W | CONVENIO Inscrito RAN / Programado | 24 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| X | Realizado | 21 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| Y | ASAMBLEA DE ANUENCIA Y APROBACIÓN DE CONVENIO SUPERFICIE ADICIONAL / Caminamiento / Programado | 27 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| Z | Realizado | 21 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AA | Asambleas / Programado | 24 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AB | Realizado | 21 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AC | Ingreso al RAN / Programado | 24 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AD | Realizado | 21 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AE | Acta Inscrita en el RAN / Programado | 24 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AF | Realizado | 21 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AG | Convenio firmado / Programado | 24 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AH | Realizado | 21 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AI | CONVENIO  Ingreso al RAN / Programado | 24 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AJ | Realizado | 21 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AK | CONVENIO Inscrito RAN / Programado | 24 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AL | Realizado | 21 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AM | OBRAS COMPLEMENTARIAS / Caminamiento / Programado | 27 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AN | Realizado | 27 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AO | Asambleas para aceptación de firma de COP / Programado | 24 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AP | Realizado | 21 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AQ | Ingreso al RAN / Programado | 24 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AR | Realizado | 21 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AS | Acta Inscrita en el RAN / Programado | 24 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AT | Realizado | 21 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AU | Convenio firmado / Programado | 24 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AV | Realizado | 21 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AW | CONVENIO Ingreso al RAN / Programado | 24 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AX | Realizado | 21 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AY | CONVENIO Inscrito RAN / Programado | 24 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AZ | Realizado | 21 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| BA | ASAMBLEAS RETIRO DE FONDOS / Asamblea / Programado | 27 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| BB | Realizado | 21 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| BC | Ingreso al RAN / Programado | 24 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| BD | Realizado | 21 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| BE | Acta Inscrita en el RAN / Programado | 24 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| BF | Realizado | 21 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| BG | Expropiación directa | 21 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| BH | Indicador BH | 0 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| BI | Indicador BI | 0 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| BJ | Indicador BJ | 0 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| BK | Indicador BK | 0 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| BL | Indicador BL | 1 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |

## `PROYECTOS VÍAS SEGUIMIENTO GENERAL.xlsx` - `COP´S COLECTIVOS`

Clasificación: **B. REPORTE / DERIVADO**. Resumen de COP colectivos por proyecto, destino y tipo de convenio.

| Col. | Columna fuente | Filas con dato | Estado | Tipo de tratamiento | Entidad destino | Campo destino | Persiste | Deriva | Referencia | Requiere decisión | Observación |
|---:|---|---:|---|---|---|---|---:|---:|---:|---:|---|
| A | DESTINO DE SUPERFICIE | 15 | DOCUMENTAR | documentar | `dashboard` | `dimension_reporte` | No | Si | No | No | Dimension de reporte; se alimenta desde hechos capturados. |
| B | OCUPACIÓN PREVIA / COP´S FIRMADOS / M-Q | 24 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| C | A-P | 16 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| D | Q-I | 16 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| E | S-NL | 16 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| F | DOS BOCAS | 16 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| G | COP´S INGRESADOS / M-Q | 20 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| H | A-P | 16 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| I | Q-I | 16 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| J | S-NL | 16 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| K | DOS BOCAS | 16 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| L | COP´S INSCRITOS / M-Q | 20 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| M | A-P | 16 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| N | Q-I | 16 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| O | S-NL | 16 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| P | DOS BOCAS | 16 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| Q | MODIFICATORIO / COP´S FIRMADOS / M-Q | 18 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| R | A-P | 12 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| S | Q-I | 10 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| T | S-NL | 12 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| U | DOS BOCAS | 10 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| V | COP´S INGRESADOS / M-Q | 15 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| W | A-P | 12 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| X | Q-I | 10 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| Y | S-NL | 12 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| Z | DOS BOCAS | 10 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AA | COP´S INSCRITOS / M-Q | 15 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AB | A-P | 12 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AC | Q-I | 10 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AD | S-NL | 12 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AE | DOS BOCAS | 10 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AF | SUP. ADICIONAL / COP´S FIRMADOS / M-Q | 18 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AG | A-P | 12 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AH | Q-I | 10 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AI | S-NL | 12 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AJ | DOS BOCAS | 10 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AK | COP´S INGRESADOS / M-Q | 15 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AL | A-P | 12 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AM | Q-I | 10 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AN | S-NL | 12 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AO | DOS BOCAS | 10 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AP | COP´S INSCRITOS / M-Q | 15 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AQ | A-P | 12 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AR | Q-I | 10 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AS | S-NL | 10 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AT | DOS BOCAS | 12 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AU | OBRAS COMPLEMENTARIAS / COP´S FIRMADOS / M-Q | 18 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AV | A-P | 12 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AW | Q-I | 10 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AX | S-NL | 12 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AY | DOS BOCAS | 10 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| AZ | COP´S INGRESADOS / M-Q | 15 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| BA | A-P | 12 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| BB | Q-I | 10 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| BC | S-NL | 12 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| BD | DOS BOCAS | 10 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| BE | COP´S INSCRITOS / M-Q | 15 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| BF | A-P | 12 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| BG | Q-I | 10 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| BH | S-NL | 12 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| BI | DOS BOCAS | 10 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |

## `PROYECTOS VÍAS SEGUIMIENTO GENERAL.xlsx` - `INDIVIDUALES`

Clasificación: **B. REPORTE / DERIVADO**. Resumen de COP individuales, parcelas y ampliaciones por proyecto.

| Col. | Columna fuente | Filas con dato | Estado | Tipo de tratamiento | Entidad destino | Campo destino | Persiste | Deriva | Referencia | Requiere decisión | Observación |
|---:|---|---:|---|---|---|---|---:|---:|---:|---:|---|
| A | PROYECTO | 23 | DOCUMENTAR | documentar | `dashboard` | `dimension_reporte` | No | Si | No | No | Dimension de reporte; se alimenta desde hechos capturados. |
| B | NO. TOTAL DE PARCELAS AFECTADAS | 17 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| C | COP FIRMADOS / Programado | 28 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| D | Realizado | 21 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| E | COP INGRESO AL RAN / Programado | 24 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| F | Realizado | 19 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| G | COP INSCRITOS AL RAN / Programado | 29 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| H | Realizado | 26 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| I | CONVENIO MODIFICATORIO FIRMADOS / Programado | 29 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| J | Realizado | 26 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| K | CONVENIO MODIFICATORIO INGRESO AL RAN / Programado | 22 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| L | Realizado | 26 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| M | CONVENIO MODIFICATORIO INSCRITOS AL RAN / Programado | 29 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| N | Realizado | 19 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| O | COP AMPLIACIÓN FIRMADOS / Programado | 22 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| P | Realizado | 19 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| Q | COP AMPLIACIÓN INGRESO AL RAN / Programado | 22 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| R | Realizado | 19 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| S | COP AMPLIACIÓN INSCRITOS / Programado | 22 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| T | Realizado | 19 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |

## `SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS-INDIVIDUALES-MQ.xlsx` - `General `

Clasificación: **B. REPORTE / DERIVADO**. Resumen compacto de ruta individual/colectiva; sirve para contraste, no como tabla nueva.

| Col. | Columna fuente | Filas con dato | Estado | Tipo de tratamiento | Entidad destino | Campo destino | Persiste | Deriva | Referencia | Requiere decisión | Observación |
|---:|---|---:|---|---|---|---|---:|---:|---:|---:|---|
| A | Num. | 18 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| B | Municipio | 0 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| C | Núcleo agrario | 0 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| D | N° de Ejidatarios de acuerdo a padrón | 1 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| E | Acta de elección inscrita en RAN | 0 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| F | Superficie afectable / Tierras de Uso Común ó infraestructura | 1 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| G | Tierras Parceladas (Parcela Escolar, UAIM, de la Juventud, etc.) a favor del ejido | 1 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| H | Asamblea de Anuencia y aprobación de Convenio de ocupación previa COP (fecha) | 0 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| I | Asamblea de firma de convenio de Ocupación previa y Pago de Indemnización (fecha) | 0 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| J | Entrega de expediente SICT - Procuraduría Agraria (fecha) | 0 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| K | Ingreso de Expediente al RAN Acta de asamblea / Fecha | 1 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| L | N° Solicitud de tramite | 1 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| M | Inscipción RAN (fecha y folio) | 0 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| N | Ingreso de Expediente al RAN Convenio de ocupación previa / Fecha | 1 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| O | N° Solicitud de tramite | 1 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| P | Inscipción RAN | 0 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| Q | Observaciones | 0 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| R | Validación PA/SICT | 0 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |

## `SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS-INDIVIDUALES-MQ.xlsx` - `PROPUESTA`

Clasificación: **A. FUENTE DETALLADA**. Fuente detallada principal de derechos individuales Mexico-Queretaro.

| Col. | Columna fuente | Filas con dato | Estado | Tipo de tratamiento | Entidad destino | Campo destino | Persiste | Deriva | Referencia | Requiere decisión | Observación |
|---:|---|---:|---|---|---|---|---:|---:|---:|---:|---|
| A | NUM. | 683 | DOCUMENTAR | documentar | `importacion_excel` | `source_row/source_index` | Si | No | Si | No | Identificador de conciliación de fuente; no es entidad de negocio. |
| B | ENTIDAD | 774 | PERSISTIR | persistir | `entidad_federativa` | `nombre/clave` | Si | No | No | No | Resolver catalogo territorial. |
| C | MUNICIPIO | 775 | PERSISTIR | persistir | `municipio` | `nombre/clave_inegi` | Si | No | No | No | Resolver catalogo territorial. |
| D | RESIDENCIA | 743 | PERSISTIR | persistir | `proyecto_nucleo` | `residencia` | Si | No | No | No | Dato del seguimiento del núcleo dentro del proyecto. |
| E | CONSECUTIVO | 743 | PERSISTIR | persistir | `proyecto_nucleo` | `consecutivo` | Si | No | No | No | Consecutivo operativo por proyecto/núcleo. |
| F | NÚCLEO AGRARIO | 774 | PERSISTIR | persistir | `nucleo_agrario` | `nombre` | Si | No | No | No | Crear o resolver núcleo dentro del contexto de proyecto. |
| G | E/C | 774 | PERSISTIR | persistir | `nucleo_agrario` | `tipo_nucleo` | Si | No | No | No | Normalizar E/C a ejido/comunidad. |
| H | NOMBRE DE LA PERSONA ORGANIZADORA AGRARIA RESPONSABLE | 627 | PERSISTIR | persistir | `proyecto_nucleo` | `responsable_nombre` | Si | No | No | No | Responsable operativo. |
| I | DATOS DE CONTACTO (TELÉFONO) | 559 | PERSISTIR | persistir | `proyecto_nucleo` | `responsable_contacto` | Si | No | No | No | Telefono/contacto operativo. |
| J | TIPO DE PARCELA (INDIVIDUAL) | 746 | PERSISTIR | persistir | `parcela` | `tipo_parcela` | Si | No | No | No | Parcela es eje de derechos individuales. |
| K | NO. DE PARCELA | 310 | PERSISTIR | persistir | `parcela` | `numero_parcela` | Si | No | No | No | Identificador de parcela. |
| L | NO. DE PARCELA PPT | 747 | PERSISTIR | persistir | `parcela` | `numero_parcela_ppt` | Si | No | No | No | Identificador PPT de fuente. |
| M | NOMBRE DE LA PERSONA TITULAR DE LA PARCELA | 748 | PERSISTIR | persistir | `persona/parcela_titular` | `nombre_literal_fuente` | Si | No | No | No | Normalizar persona y conservar literal de fuente. |
| N | CONSTANCIA DE VIGENCIA DE DERECHOS (FECHA) | 491 | PERSISTIR | persistir | `parcela` | `constancia_vigencia_fecha` | Si | No | No | No | Dato documental de parcela. |
| O | CERTIFICADO PARCELARIO | 631 | PERSISTIR | persistir | `parcela` | `certificado_parcelario` | Si | No | No | No | Dato documental de parcela. |
| P | FOLIO DE DERECHOS | 386 | PERSISTIR | persistir | `parcela` | `folio_derechos` | Si | No | No | No | Dato documental de parcela. |
| Q | CLAVE DEL TRAMO | 651 | REFERENCIA | referencia | `proyecto_nucleo` | `clave_tramo_referencia` | Si | No | Si | No | Referencia histórica opcional; no crea entidad Tramo. |
| R | NÚMERO DE TRAMO | 0 | REFERENCIA | referencia | `proyecto_nucleo` | `numero_tramo_referencia` | Si | No | Si | No | Referencia histórica opcional; no crea entidad Tramo. |
| S | CONVENIO FIRMADO (FECHA) | 495 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| T | CONVENIO MONTO 90% | 300 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| U | CONVENIO MONTO 100% | 480 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| V | MONTO BDT | 10 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| W | TRIMESTRE | 495 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| X | CONVENIO INGRESADO AL RAN (FECHA) | 429 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| Y | NO. DE SOLICITUD DE INGRESO | 429 | PERSISTIR | persistir | `convenio` | `numero_solicitud_ingreso` | Si | No | No | No | Solicitud RAN del convenio; no usar campo_fuente_revision. |
| Z | TRIMESTRE2 | 429 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| AA | CALIFICACIÓN REGISTRAL | 81 | DOCUMENTAR | documentar | `observacion/importacion_excel` | `valor_fuente` | Si | No | Si | No | Campo no estructurado; preservar durante migración para conciliación. |
| AB | CONVENIO INSCRITO EN EL RAN (FECHA) | 346 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| AC | TRIMESTRE22 | 346 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| AD | SUPERFICIE TOTAL (HA). | 469 | PERSISTIR | persistir | `afectacion` | `superficie_afectada_ha` | Si | No | No | No | Dato administrativo capturado. |
| AE | CONVENIO MODIFICATORIO (FECHA) | 1 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo modificatorio)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| AF | CONVENIO MONTO 90%2 | 0 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| AG | CONVENIO MONTO 100% 2 | 1 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| AH | TRIMESTRE4 | 1 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| AI | CONVENIO AMPLIACIÓN (FECHA) | 119 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo ampliacion)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| AJ | CONVENIO MONTO 90%.. | 78 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| AK | CONVENIO MONTO 100% .. | 119 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| AL | MONTO BDT2 | 18 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| AM | TRIMESTRE3 | 120 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| AN | CONVENIO INGRESADO AL RAN (FECHA)2 | 57 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| AO | NO. DE SOLICITUD DE INGRESO3 | 57 | PERSISTIR | persistir | `convenio` | `numero_solicitud_ingreso` | Si | No | No | No | Solicitud RAN del convenio; no usar campo_fuente_revision. |
| AP | TRIMESTRE24 | 57 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| AQ | CALIFICACIÓN REGISTRAL2 | 0 | DOCUMENTAR | documentar | `observacion/importacion_excel` | `valor_fuente` | Si | No | Si | No | Campo no estructurado; preservar durante migración para conciliación. |
| AR | CONVENIO INSCRITO EN EL RAN (FECHA)3 | 16 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| AS | TRIMESTRE224 | 16 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| AT | SUPERFICIE DE AMPLIACIÓN | 119 | PERSISTIR | persistir | `convenio` | `superficie_ha (ampliacion/ampliacion_remanente)` | Si | No | No | No | Superficie propia de la ampliación. |
| AU | CONVENIO AMPLIACIÓN 2 (FECHA). | 3 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo ampliacion_remanente)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| AV | CONVENIO MONTO 90%..3 | 2 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| AW | CONVENIO MONTO 100% ..4 | 3 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| AX | MONTO BDT25 | 0 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| AY | TRIMESTRE36 | 3 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| AZ | CONVENIO INGRESADO AL RAN (FECHA)27 | 1 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| BA | NO. DE SOLICITUD DE INGRESO38 | 1 | PERSISTIR | persistir | `convenio` | `numero_solicitud_ingreso` | Si | No | No | No | Solicitud RAN del convenio; no usar campo_fuente_revision. |
| BB | TRIMESTRE249 | 1 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| BC | CALIFICACIÓN REGISTRAL210 | 0 | DOCUMENTAR | documentar | `observacion/importacion_excel` | `valor_fuente` | Si | No | Si | No | Campo no estructurado; preservar durante migración para conciliación. |
| BD | CONVENIO INSCRITO EN EL RAN (FECHA)311 | 0 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| BE | TRIMESTRE22412 | 0 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| BF | SUPERFICIE DE AMPLIACIÓN2 | 3 | PERSISTIR | persistir | `convenio` | `superficie_ha (ampliacion/ampliacion_remanente)` | Si | No | No | No | Superficie propia de la ampliación. |
| BG | ESTATUS (COMPLETO, PENDIENTE, PROGRAMADO) | 11 | PERSISTIR | persistir | `indemnizacion` | `estatus` | Si | No | No | No | No equivale a pago; pago es hecho financiero separado. |
| BH | ENTREGA DE EXPEDIENTE SICT - PROCURADURÍA AGRARIA. | 0 | DOCUMENTAR | documentar | `ninguna` | `campo_reservado` | No | No | No | No | Sin datos en auditoría local; no crear módulo hasta confirmar uso. |
| BI | NO. DE OFICIO FIFONAFE A DGAOPR/REPRESENTACIÓN Y FECHA | 274 | PERSISTIR | persistir | `tramite_fifonafe` | `cuatro_oficios_fechas_resultado_estatus` | Si | No | No | No | Conservar oficio FIFONAFE, oficio DGAOPR, respuesta Representación y respuesta final. |
| BJ | NO. DE OFICIO DGAOPR A REPRESENTACIÓN Y FECHA | 153 | PERSISTIR | persistir | `tramite_fifonafe` | `cuatro_oficios_fechas_resultado_estatus` | Si | No | No | No | Conservar oficio FIFONAFE, oficio DGAOPR, respuesta Representación y respuesta final. |
| BK | RESPUESTA  REPRESENTACIÓN A DGAOPR NO. DE OFICIO Y FECHA | 236 | PERSISTIR | persistir | `tramite_fifonafe` | `cuatro_oficios_fechas_resultado_estatus` | Si | No | No | No | Conservar oficio FIFONAFE, oficio DGAOPR, respuesta Representación y respuesta final. |
| BL | RESPUESTA DGAOPR/REPRESENTACIÓN A FIFONAFE NO. DE OFICIO Y FECHA | 243 | PERSISTIR | persistir | `tramite_fifonafe` | `cuatro_oficios_fechas_resultado_estatus` | Si | No | No | No | Conservar oficio FIFONAFE, oficio DGAOPR, respuesta Representación y respuesta final. |
| BM | OBSERVACIONES / ACUERDOS | 0 | PERSISTIR | persistir | `observacion/documento_soporte` | `observaciones` | Si | No | No | No | Preservar texto literal; estructurar sólo si hay ciclo de vida propio. |
| BN | VALIDACIÓN PA/SICT | 0 | DOCUMENTAR | documentar | `ninguna` | `campo_reservado` | No | No | No | No | Sin datos en auditoría local; no crear módulo hasta confirmar uso. |
| BO | OFICIO RAN  PARCELAS CON AFECTACIÓN | 52 | REFERENCIA | referencia | `documento_soporte` | `referencia_oficio_ran_parcelas` | Si | No | Si | No | Referencia documental asociada a parcelas/afectaciones. |
| BP | OBSERVACIONES | 243 | PERSISTIR | persistir | `observacion/documento_soporte` | `observaciones` | Si | No | No | No | Preservar texto literal; estructurar sólo si hay ciclo de vida propio. |
| BQ | *SOPORTE | 521 | PERSISTIR | persistir | `documento_soporte` | `descripcion/archivo/referencia` | Si | No | No | No | Soporte documental de la fuente. |

## `SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS-INDIVIDUALES-MQ.xlsx` - `COP´S PENDIENTES`

Clasificación: **A. FUENTE DETALLADA**. Fuente detallada filtrada/control de COP pendientes; se concilia contra PROPUESTA para evitar duplicados.

| Col. | Columna fuente | Filas con dato | Estado | Tipo de tratamiento | Entidad destino | Campo destino | Persiste | Deriva | Referencia | Requiere decisión | Observación |
|---:|---|---:|---|---|---|---|---:|---:|---:|---:|---|
| A | NUM. | 687 | DOCUMENTAR | documentar | `importacion_excel` | `source_row/source_index` | Si | No | Si | No | Identificador de conciliación de fuente; no es entidad de negocio. |
| B | ENTIDAD | 687 | PERSISTIR | persistir | `entidad_federativa` | `nombre/clave` | Si | No | No | No | Resolver catalogo territorial. |
| C | MUNICIPIO | 688 | PERSISTIR | persistir | `municipio` | `nombre/clave_inegi` | Si | No | No | No | Resolver catalogo territorial. |
| D | RESIDENCIA | 687 | PERSISTIR | persistir | `proyecto_nucleo` | `residencia` | Si | No | No | No | Dato del seguimiento del núcleo dentro del proyecto. |
| E | CONSECUTIVO | 687 | PERSISTIR | persistir | `proyecto_nucleo` | `consecutivo` | Si | No | No | No | Consecutivo operativo por proyecto/núcleo. |
| F | NÚCLEO AGRARIO | 687 | PERSISTIR | persistir | `nucleo_agrario` | `nombre` | Si | No | No | No | Crear o resolver núcleo dentro del contexto de proyecto. |
| G | E/C | 687 | PERSISTIR | persistir | `nucleo_agrario` | `tipo_nucleo` | Si | No | No | No | Normalizar E/C a ejido/comunidad. |
| H | NOMBRE DE LA PERSONA ORGANIZADORA AGRARIA RESPONSABLE | 572 | PERSISTIR | persistir | `proyecto_nucleo` | `responsable_nombre` | Si | No | No | No | Responsable operativo. |
| I | DATOS DE CONTACTO (TELÉFONO) | 504 | PERSISTIR | persistir | `proyecto_nucleo` | `responsable_contacto` | Si | No | No | No | Telefono/contacto operativo. |
| J | TIPO DE PARCELA (INDIVIDUAL) | 646 | PERSISTIR | persistir | `parcela` | `tipo_parcela` | Si | No | No | No | Parcela es eje de derechos individuales. |
| K | NO. DE PARCELA | 311 | PERSISTIR | persistir | `parcela` | `numero_parcela` | Si | No | No | No | Identificador de parcela. |
| L | NO. DE PARCELA PPT | 657 | PERSISTIR | persistir | `parcela` | `numero_parcela_ppt` | Si | No | No | No | Identificador PPT de fuente. |
| M | NOMBRE DE LA PERSONA TITULAR DE LA PARCELA | 667 | PERSISTIR | persistir | `persona/parcela_titular` | `nombre_literal_fuente` | Si | No | No | No | Normalizar persona y conservar literal de fuente. |
| N | CONSTANCIA DE VIGENCIA DE DERECHOS (FECHA) | 291 | PERSISTIR | persistir | `parcela` | `constancia_vigencia_fecha` | Si | No | No | No | Dato documental de parcela. |
| O | CERTIFICADO PARCELARIO | 470 | PERSISTIR | persistir | `parcela` | `certificado_parcelario` | Si | No | No | No | Dato documental de parcela. |
| P | FOLIO DE DERECHOS | 351 | PERSISTIR | persistir | `parcela` | `folio_derechos` | Si | No | No | No | Dato documental de parcela. |
| Q | CLAVE DEL TRAMO | 0 | REFERENCIA | referencia | `proyecto_nucleo` | `clave_tramo_referencia` | Si | No | Si | No | Referencia histórica opcional; no crea entidad Tramo. |
| R | NÚMERO DE TRAMO | 0 | REFERENCIA | referencia | `proyecto_nucleo` | `numero_tramo_referencia` | Si | No | Si | No | Referencia histórica opcional; no crea entidad Tramo. |
| S | CONVENIO FIRMADO (FECHA) | 321 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| T | CONVENIO MONTO 90% | 225 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| U | CONVENIO MONTO 100% | 319 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| V | MONTO BDT | 8 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| W | TRIMESTRE | 321 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| X | CONVENIO INGRESADO AL RAN (FECHA) | 210 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| Y | NO. DE SOLICITUD DE INGRESO | 210 | PERSISTIR | persistir | `convenio` | `numero_solicitud_ingreso` | Si | No | No | No | Solicitud RAN del convenio; no usar campo_fuente_revision. |
| Z | TRIMESTRE2 | 210 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| AA | CALIFICACIÓN REGISTRAL | 52 | DOCUMENTAR | documentar | `observacion/importacion_excel` | `valor_fuente` | Si | No | Si | No | Campo no estructurado; preservar durante migración para conciliación. |
| AB | CONVENIO INSCRITO EN EL RAN (FECHA) | 162 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| AC | TRIMESTRE22 | 161 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| AD | CONVENIO MODIFICATORIO (FECHA) | 1 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo modificatorio)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| AE | CONVENIO MONTO 90%2 | 0 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| AF | CONVENIO MONTO 100% 2 | 1 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| AG | ESTATUS (COMPLETO, PENDIENTE, PROGRAMADO) | 1 | PERSISTIR | persistir | `indemnizacion` | `estatus` | Si | No | No | No | No equivale a pago; pago es hecho financiero separado. |
| AH | ENTREGA DE EXPEDIENTE SICT - PROCURADURÍA AGRARIA. | 0 | DOCUMENTAR | documentar | `ninguna` | `campo_reservado` | No | No | No | No | Sin datos en auditoría local; no crear módulo hasta confirmar uso. |
| AI | SUPERFICIE TOTAL (HA). | 306 | PERSISTIR | persistir | `afectacion` | `superficie_afectada_ha` | Si | No | No | No | Dato administrativo capturado. |
| AJ | OBSERVACIONES / ACUERDOS | 0 | PERSISTIR | persistir | `observacion/documento_soporte` | `observaciones` | Si | No | No | No | Preservar texto literal; estructurar sólo si hay ciclo de vida propio. |
| AK | VALIDACIÓN PA/SICT | 0 | DOCUMENTAR | documentar | `ninguna` | `campo_reservado` | No | No | No | No | Sin datos en auditoría local; no crear módulo hasta confirmar uso. |
| AL | OFICIO RAN  PARCELAS CON AFECTACIÓN | 52 | REFERENCIA | referencia | `documento_soporte` | `referencia_oficio_ran_parcelas` | Si | No | Si | No | Referencia documental asociada a parcelas/afectaciones. |
| AM | OBSERVACIONES | 135 | PERSISTIR | persistir | `observacion/documento_soporte` | `observaciones` | Si | No | No | No | Preservar texto literal; estructurar sólo si hay ciclo de vida propio. |
| AN | SOPORTE DOCUMENTAL | 180 | PERSISTIR | persistir | `documento_soporte` | `descripcion/archivo/referencia` | Si | No | No | No | Soporte documental de la fuente. |

## `SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS-INDIVIDUALES-MQ.xlsx` - `Hoja2`

Clasificación: **D. HISTÓRICO / NO RELEVANTE**. Hoja vacía en la auditoría local.

| Col. | Columna fuente | Filas con dato | Estado | Tipo de tratamiento | Entidad destino | Campo destino | Persiste | Deriva | Referencia | Requiere decisión | Observación |
|---:|---|---:|---|---|---|---|---:|---:|---:|---:|---|

## `SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS-INDIVIDUALES-MQ.xlsx` - `Hoja1`

Clasificación: **C. CONTROL AUXILIAR**. Control auxiliar de COP individuales por núcleo; contiene permuta y convenio para dos solares.

| Col. | Columna fuente | Filas con dato | Estado | Tipo de tratamiento | Entidad destino | Campo destino | Persiste | Deriva | Referencia | Requiere decisión | Observación |
|---:|---|---:|---|---|---|---|---:|---:|---:|---:|---|
| B | ENTIDAD | 35 | PERSISTIR | persistir | `entidad_federativa` | `nombre/clave` | Si | No | No | No | Resolver catalogo territorial. |
| C | MUNICIPIO | 35 | PERSISTIR | persistir | `municipio` | `nombre/clave_inegi` | Si | No | No | No | Resolver catalogo territorial. |
| D | NÚCLEO AGRARIO | 36 | PERSISTIR | persistir | `nucleo_agrario` | `nombre` | Si | No | No | No | Crear o resolver núcleo dentro del contexto de proyecto. |
| E | TOTAL DE COPS | 2 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| F | FECHA PROGRAMADA PARA FIRMA | 26 | PERSISTIR | persistir | `convenio` | `fecha_programada_firma` | Si | No | No | No | Separada de ingreso RAN programado. |
| G | NO. DE COPS A FIRMAR | 8 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| H | COP FIRMADOS / INDIVIDUAL | 35 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| I | SOPORTE DOCUMENTAL | 32 | PERSISTIR | persistir | `documento_soporte` | `descripcion/archivo/referencia` | Si | No | No | No | Soporte documental de la fuente. |
| J | COP INGRESADOS AL RAN / INDIVIDUAL | 12 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| K | COP INSCRITOS / INDIVIDUAL | 10 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| L | OBSERVACIONES | 13 | PERSISTIR | persistir | `observacion/documento_soporte` | `observaciones` | Si | No | No | No | Preservar texto literal; estructurar sólo si hay ciclo de vida propio. |

## `Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx` - `General `

Clasificación: **B. REPORTE / DERIVADO**. Resumen compacto; no sustituye a INFORME M-Q ni ASAMBLEAS PENDIENTES.

| Col. | Columna fuente | Filas con dato | Estado | Tipo de tratamiento | Entidad destino | Campo destino | Persiste | Deriva | Referencia | Requiere decisión | Observación |
|---:|---|---:|---|---|---|---|---:|---:|---:|---:|---|
| A | Num. | 18 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| B | Municipio | 0 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| C | Núcleo agrario | 0 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| D | N° de Ejidatarios de acuerdo a padrón | 1 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| E | Acta de elección inscrita en RAN | 0 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| F | Superficie afectable / Tierras de Uso Común ó infraestructura | 1 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| G | Tierras Parceladas (Parcela Escolar, UAIM, de la Juventud, etc.) a favor del ejido | 1 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| H | Asamblea de Anuencia y aprobación de Convenio de ocupación previa COP (fecha) | 0 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| I | Asamblea de firma de convenio de Ocupación previa y Pago de Indemnización (fecha) | 0 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| J | Entrega de expediente SICT - Procuraduría Agraria (fecha) | 0 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| K | Ingreso de Expediente al RAN Acta de asamblea / Fecha | 1 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| L | N° Solicitud de tramite | 1 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| M | Inscipción RAN (fecha y folio) | 0 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| N | Ingreso de Expediente al RAN Convenio de ocupación previa / Fecha | 1 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| O | N° Solicitud de tramite | 1 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| P | Inscipción RAN | 0 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| Q | Observaciones | 0 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |
| R | Validación PA/SICT | 0 | DERIVAR | derivar | `dashboard/reporteador` | `indicador_calculado` | No | Si | No | No | KPI del Excel general/compacto; contrato de aceptación, no total manual persistido. |

## `Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx` - `INFORME M-Q`

Clasificación: **A. FUENTE DETALLADA**. Fuente detallada principal de derechos colectivos Mexico-Queretaro.

| Col. | Columna fuente | Filas con dato | Estado | Tipo de tratamiento | Entidad destino | Campo destino | Persiste | Deriva | Referencia | Requiere decisión | Observación |
|---:|---|---:|---|---|---|---|---:|---:|---:|---:|---|
| A | NUM. | 96 | DOCUMENTAR | documentar | `importacion_excel` | `source_row/source_index` | Si | No | Si | No | Identificador de conciliación de fuente; no es entidad de negocio. |
| B | ENTIDAD | 115 | PERSISTIR | persistir | `entidad_federativa` | `nombre/clave` | Si | No | No | No | Resolver catalogo territorial. |
| C | MUNICIPIO | 115 | PERSISTIR | persistir | `municipio` | `nombre/clave_inegi` | Si | No | No | No | Resolver catalogo territorial. |
| D | RESIDENCIA | 115 | PERSISTIR | persistir | `proyecto_nucleo` | `residencia` | Si | No | No | No | Dato del seguimiento del núcleo dentro del proyecto. |
| E | CONSECUTIVO | 115 | PERSISTIR | persistir | `proyecto_nucleo` | `consecutivo` | Si | No | No | No | Consecutivo operativo por proyecto/núcleo. |
| F | NÚCLEO AGRARIO | 115 | PERSISTIR | persistir | `nucleo_agrario` | `nombre` | Si | No | No | No | Crear o resolver núcleo dentro del contexto de proyecto. |
| G | E/C | 113 | PERSISTIR | persistir | `nucleo_agrario` | `tipo_nucleo` | Si | No | No | No | Normalizar E/C a ejido/comunidad. |
| H | NOMBRE DE LA PERSONA ORGANIZADORA AGRARIA RESPONSABLE | 85 | PERSISTIR | persistir | `proyecto_nucleo` | `responsable_nombre` | Si | No | No | No | Responsable operativo. |
| I | DATOS DE CONTACTO (TELÉFONO) | 82 | PERSISTIR | persistir | `proyecto_nucleo` | `responsable_contacto` | Si | No | No | No | Telefono/contacto operativo. |
| J | DESTINO DE LA SUPERFICIE | 87 | PERSISTIR | persistir | `afectacion_colectiva` | `destino_superficie` | Si | No | No | No | Permite TUC, parcela escolar, UAIM, canal, derecho de paso, solares u otro. |
| K | NO. DE PARCELA/SOLAR | 37 | REFERENCIA | referencia | `afectacion_colectiva` | `referencia_parcela_solar` | Si | No | Si | No | Colectivo no exige parcela; se conserva referencia si existe. |
| L | FECHA DE PADRÓN | 100 | PERSISTIR | persistir | `padron_historial` | `fecha_padron` | Si | No | No | No | Historial del padrón del núcleo. |
| M | PADRÓN: NÚMERO DE EJIDATARIOS/ COMUNEROS | 76 | PERSISTIR | persistir | `padron_historial` | `numero_ejidatarios_comuneros` | Si | No | No | No | Dato de padrón del núcleo. |
| N | ORV VIGENTES (SI/NO) | 114 | PERSISTIR | persistir | `orv` | `vigencia/integrantes/acta_eleccion_inscrita_ran` | Si | No | No | No | Datos de órganos de representación y vigilancia. |
| O | FECHA DE VENCIMIENTO DE ORV | 114 | PERSISTIR | persistir | `orv` | `vigencia/integrantes/acta_eleccion_inscrita_ran` | Si | No | No | No | Datos de órganos de representación y vigilancia. |
| P | ACTA DE ELECCIÓN DE ORV INSCRITA EN EL RAN (SI/NO) | 104 | PERSISTIR | persistir | `orv` | `vigencia/integrantes/acta_eleccion_inscrita_ran` | Si | No | No | No | Datos de órganos de representación y vigilancia. |
| Q | CLAVE DEL TRAMO | 0 | REFERENCIA | referencia | `proyecto_nucleo` | `clave_tramo_referencia` | Si | No | Si | No | Referencia histórica opcional; no crea entidad Tramo. |
| R | NÚMERO DE TRAMO | 0 | REFERENCIA | referencia | `proyecto_nucleo` | `numero_tramo_referencia` | Si | No | Si | No | Referencia histórica opcional; no crea entidad Tramo. |
| S | REUNIÓN PROGRAMADA (FECHA) | 104 | PERSISTIR | persistir | `actividad_campo` | `sensibilizacion.fecha_programada_o_realizada` | Si | No | No | No | Actividad del proyecto_nucleo o del contexto de convenio adicional. |
| T | PROGRAMADA POR NA | 75 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| U | REUNIÓN REALIZADA (FECHA) | 104 | PERSISTIR | persistir | `actividad_campo` | `sensibilizacion.fecha_programada_o_realizada` | Si | No | No | No | Actividad del proyecto_nucleo o del contexto de convenio adicional. |
| V | REALIZADA POR NA | 65 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| W | TRIMESTRE | 65 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| X | PROGRAMADO (FECHA) | 104 | PERSISTIR | persistir | `actividad_campo` | `caminamiento.fecha_programada_o_realizada` | Si | No | No | No | Actividad administrativa; no calcula superficie oficial. |
| Y | PROGRAMADO POR NA | 65 | DOCUMENTAR | documentar | `observacion/importacion_excel` | `valor_fuente` | Si | No | Si | No | Campo no estructurado; preservar durante migración para conciliación. |
| Z | REALIZADO (FECHA) | 104 | PERSISTIR | persistir | `actividad_campo` | `caminamiento.fecha_programada_o_realizada` | Si | No | No | No | Actividad administrativa; no calcula superficie oficial. |
| AA | REALIZADO POR NA | 65 | DOCUMENTAR | documentar | `observacion/importacion_excel` | `valor_fuente` | Si | No | Si | No | Campo no estructurado; preservar durante migración para conciliación. |
| AB | TRIMESTRE5 | 65 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| AC | ASAMBLEA  PROGRAMADA 1/a (FECHA) | 95 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |
| AD | ASAMBLEA  PROGRAMADA 2/a (FECHA) | 64 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |
| AE | PROGRAMADA POR NA2 | 52 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| AF | ASAMBLEA  REALIZADA (FECHA) | 93 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |
| AG | REALIZADA POR NA2 | 52 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| AH | TRIMESTRE6 | 52 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| AI | FECHA PROGRAMADA DE INGRESO AL RAN | 0 | PERSISTIR | persistir | `asamblea` | `fecha_programada_ingreso_ran` | Si | No | No | No | RAN del acta. |
| AJ | INGRESADO AL RAN (FECHA) | 75 | PERSISTIR | persistir | `asamblea` | `fecha_ingreso_ran` | Si | No | No | No | RAN del acta, separado del RAN del convenio. |
| AK | NÚMERO DE SOLICITUD DE INGRESO | 75 | PERSISTIR | persistir | `asamblea` | `numero_solicitud_ran` | Si | No | No | No | Solicitud RAN del acta, separada del convenio. |
| AL | INGRESO POR NA | 45 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| AM | TRIMESTRE7 | 45 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| AN | CALIFICACIÓN REGISTRAL3 | 5 | DOCUMENTAR | documentar | `observacion/importacion_excel` | `valor_fuente` | Si | No | Si | No | Campo no estructurado; preservar durante migración para conciliación. |
| AO | ACTA INSCRITA EN EL RAN (FECHA) | 45 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |
| AP | IINSCRITO POR NA | 32 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| AQ | TRIMESTRE8 | 32 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| AR | ACTA COMPLEMENTARIA | 0 | DOCUMENTAR | documentar | `observacion/importacion_excel` | `valor_fuente` | Si | No | Si | No | Campo no estructurado; preservar durante migración para conciliación. |
| AS | ACUSE FIFONAFE (FECHA) | 0 | PERSISTIR | persistir | `tramite_fifonafe` | `cuatro_oficios_fechas_resultado_estatus` | Si | No | No | No | Conservar oficio FIFONAFE, oficio DGAOPR, respuesta Representación y respuesta final. |
| AT | AVALÚO MAESTRO (INDAABIN) $ | 11 | PERSISTIR | persistir | `afectacion` | `avaluo_monto` | Si | No | No | No | Campo simple; institucion INDAABIN cuando corresponda. |
| AU | FECHA PROGRAMADA PARA FIRMA DE CONVENIO | 4 | PERSISTIR | persistir | `convenio` | `fecha_programada_firma` | Si | No | No | No | Separada de ingreso RAN programado. |
| AV | CONVENIO FIRMADO (FECHA) | 76 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| AW | CONVENIO MONTO 90% | 69 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| AX | CONVENIO MONTO 100% | 73 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| AY | MONTO BDT | 0 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| AZ | TRIMESTRE2 | 76 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| BA | FECHA PROGRAMADA DE INGRESO AL RAN. | 0 | PERSISTIR | persistir | `convenio` | `fecha_programada_ingreso_ran` | Si | No | No | No | Separada de firma programada. |
| BB | INGRESADO AL RAN (FECHA). | 72 | PERSISTIR | persistir | `asamblea` | `fecha_ingreso_ran` | Si | No | No | No | RAN del acta, separado del RAN del convenio. |
| BC | NÚMERO DE SOLICITUD DE INGRESO. | 72 | PERSISTIR | persistir | `convenio` | `numero_solicitud_ingreso` | Si | No | No | No | Solicitud RAN del convenio; no usar campo_fuente_revision. |
| BD | TRIMESTRE3 | 72 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| BE | CALIFICACIÓN REGISTRAL2 | 2 | DOCUMENTAR | documentar | `observacion/importacion_excel` | `valor_fuente` | Si | No | Si | No | Campo no estructurado; preservar durante migración para conciliación. |
| BF | CONVENIO INSCRITO EN EL RAN (FECHA) | 42 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| BG | TRIMESTRE4 | 42 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| BH | SUPERFICIE TOTAL  PRELIMINAR (HA) | 11 | PERSISTIR | persistir | `afectacion` | `superficie_preliminar_ha` | Si | No | No | No | No colapsar con superficie real afectada. |
| BI | SUPERFICIE TOTAL REAL AFECTADA (HA)2 | 73 | PERSISTIR | persistir | `afectacion` | `superficie_afectada_ha` | Si | No | No | No | Dato administrativo capturado; no ST_Area oficial. |
| BJ | ASAMBLEA  PROGRAMADA 1/a (FECHA)2 | 1 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |
| BK | ASAMBLEA  PROGRAMADA 2/a (FECHA)3 | 0 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |
| BL | ASAMBLEA REALIZADA (FECHA)2 | 0 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |
| BM | INGRESADO AL RAN (FECHA)3 | 0 | PERSISTIR | persistir | `asamblea` | `fecha_ingreso_ran` | Si | No | No | No | RAN del acta, separado del RAN del convenio. |
| BN | NÚMERO DE SOLICITUD DE INGRESO4 | 0 | PERSISTIR | persistir | `asamblea` | `numero_solicitud_ran` | Si | No | No | No | Solicitud RAN del acta, separada del convenio. |
| BO | ACTA INSCRITA EN EL RAN (FECHA)2 | 0 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |
| BP | CONVENIO MODIFICATORIO FIRMADO (FECHA) | 0 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo modificatorio)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| BQ | CONVENIO MONTO 90%3 | 0 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| BR | CONVENIO MONTO 100% 2 | 0 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| BS | MONTO BDT2 | 0 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| BT | TRIMESTRE22 | 0 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| BU | INGRESADO AL RAN (FECHA).3 | 0 | PERSISTIR | persistir | `asamblea` | `fecha_ingreso_ran` | Si | No | No | No | RAN del acta, separado del RAN del convenio. |
| BV | NÚMERO DE SOLICITUD DE INGRESO.4 | 0 | PERSISTIR | persistir | `convenio` | `numero_solicitud_ingreso` | Si | No | No | No | Solicitud RAN del convenio; no usar campo_fuente_revision. |
| BW | CONVENIO INSCRITO EN EL RAN (FECHA)2 | 0 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| BX | SUPERFICIE TOTAL REAL AFECTADA (HA)22 | 0 | PERSISTIR | persistir | `afectacion` | `superficie_afectada_ha` | Si | No | No | No | Dato administrativo capturado; no ST_Area oficial. |
| BY | REUNIÓN DE SENSIBILIZACIÓN PROGRAMADA (FECHA)2 | 1 | PERSISTIR | persistir | `actividad_campo` | `sensibilizacion.fecha_programada_o_realizada` | Si | No | No | No | Actividad del proyecto_nucleo o del contexto de convenio adicional. |
| BZ | REUNIÓN DE SENSIBILIZACIÓN REALIZADA (FECHA) | 0 | PERSISTIR | persistir | `actividad_campo` | `sensibilizacion.fecha_programada_o_realizada` | Si | No | No | No | Actividad del proyecto_nucleo o del contexto de convenio adicional. |
| CA | CAMINAMIENTO PROGRAMADO (FECHA)2 | 1 | PERSISTIR | persistir | `actividad_campo` | `caminamiento.fecha_programada_o_realizada` | Si | No | No | No | Actividad administrativa; no calcula superficie oficial. |
| CB | PROGRAMADO POR NA3 | 1 | DOCUMENTAR | documentar | `observacion/importacion_excel` | `valor_fuente` | Si | No | Si | No | Campo no estructurado; preservar durante migración para conciliación. |
| CC | CAMINAMIENTO REALIZADO (FECHA)4 | 1 | PERSISTIR | persistir | `actividad_campo` | `caminamiento.fecha_programada_o_realizada` | Si | No | No | No | Actividad administrativa; no calcula superficie oficial. |
| CD | REALIZADO POR NA5 | 1 | DOCUMENTAR | documentar | `observacion/importacion_excel` | `valor_fuente` | Si | No | Si | No | Campo no estructurado; preservar durante migración para conciliación. |
| CE | TRIMESTRE56 | 1 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| CF | ASAMBLEA  PROGRAMADA 1/a (FECHA)22 | 1 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |
| CG | ASAMBLEA  PROGRAMADA 2/a (FECHA)33 | 0 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |
| CH | TRIMESTRE10 | 1 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| CI | ASAMBLEA REALIZADA (FECHA)24 | 1 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |
| CJ | TRIMESTRE102 | 1 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| CK | INGRESADO AL RAN (FECHA)35 | 1 | PERSISTIR | persistir | `asamblea` | `fecha_ingreso_ran` | Si | No | No | No | RAN del acta, separado del RAN del convenio. |
| CL | NÚMERO DE SOLICITUD DE INGRESO46 | 1 | PERSISTIR | persistir | `asamblea` | `numero_solicitud_ran` | Si | No | No | No | Solicitud RAN del acta, separada del convenio. |
| CM | TRIMESTRE1022 | 1 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| CN | ACTA INSCRITA EN EL RAN (FECHA)27 | 0 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |
| CO | CONVENIO SUP. ADICIONAL FIRMADO (FECHA)2 | 5 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo superficie_adicional)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| CP | CONVENIO MONTO 90%2 | 4 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| CQ | CONVENIO MONTO 100% 3 | 5 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| CR | MONTO BDT4 | 0 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| CS | TRIMESTRE103 | 5 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| CT | INGRESADO AL RAN (FECHA).33 | 1 | PERSISTIR | persistir | `asamblea` | `fecha_ingreso_ran` | Si | No | No | No | RAN del acta, separado del RAN del convenio. |
| CU | NÚMERO DE SOLICITUD DE INGRESO.44 | 1 | PERSISTIR | persistir | `convenio` | `numero_solicitud_ingreso` | Si | No | No | No | Solicitud RAN del convenio; no usar campo_fuente_revision. |
| CV | CONVENIO INSCRITO EN EL RAN (FECHA)25 | 0 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| CW | SUPERFICIE ADICIONAL (HA)22 | 5 | PERSISTIR | persistir | `convenio` | `superficie_ha (tipo superficie_adicional)` | Si | No | No | No | Superficie propia del convenio adicional. |
| CX | REUNIÓN DE SENSIBILIZACIÓN PROGRAMADA (FECHA)2 | 0 | PERSISTIR | persistir | `actividad_campo` | `sensibilizacion.fecha_programada_o_realizada` | Si | No | No | No | Actividad del proyecto_nucleo o del contexto de convenio adicional. |
| CY | REUNIÓN DE SENSIBILIZACIÓN REALIZADA (FECHA) | 0 | PERSISTIR | persistir | `actividad_campo` | `sensibilizacion.fecha_programada_o_realizada` | Si | No | No | No | Actividad del proyecto_nucleo o del contexto de convenio adicional. |
| CZ | CAMINAMIENTO PROGRAMADO (FECHA). | 1 | PERSISTIR | persistir | `actividad_campo` | `caminamiento.fecha_programada_o_realizada` | Si | No | No | No | Actividad administrativa; no calcula superficie oficial. |
| DA | CAMINAMIENTO REALIZADO (FECHA). | 1 | PERSISTIR | persistir | `actividad_campo` | `caminamiento.fecha_programada_o_realizada` | Si | No | No | No | Actividad administrativa; no calcula superficie oficial. |
| DB | ASAMBLEA  1A CONVOCATORIA (FECHA). | 2 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |
| DC | ASAMBLEA  2A CONVOCATORIA (FECHA). | 2 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |
| DD | ASAMBLEA  REALIZADA (FECHA). | 2 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |
| DE | TRIMESTRE. | 2 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| DF | INGRESADO AL RAN (FECHA).2 | 0 | PERSISTIR | persistir | `asamblea` | `fecha_ingreso_ran` | Si | No | No | No | RAN del acta, separado del RAN del convenio. |
| DG | NÚMERO DE SOLICITUD DE INGRESO.2 | 0 | PERSISTIR | persistir | `asamblea` | `numero_solicitud_ran` | Si | No | No | No | Solicitud RAN del acta, separada del convenio. |
| DH | TRIMESTRE.2 | 0 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| DI | CALIFICACIÓN REGISTRAL.. | 0 | DOCUMENTAR | documentar | `observacion/importacion_excel` | `valor_fuente` | Si | No | Si | No | Campo no estructurado; preservar durante migración para conciliación. |
| DJ | ACTA INSCRITA EN EL RAN (FECHA). | 0 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |
| DK | TRIMESTRE9 | 0 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| DL | CONVENIO FIRMADO (FECHA). | 2 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| DM | CONVENIO MONTO 90%. | 2 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| DN | CONVENIO MONTO 100% . | 2 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| DO | TRIMESTRE11 | 2 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| DP | INGRESADO AL RAN (FECHA).. | 0 | PERSISTIR | persistir | `asamblea` | `fecha_ingreso_ran` | Si | No | No | No | RAN del acta, separado del RAN del convenio. |
| DQ | NÚMERO DE SOLICITUD DE INGRESO.. | 0 | PERSISTIR | persistir | `convenio` | `numero_solicitud_ingreso` | Si | No | No | No | Solicitud RAN del convenio; no usar campo_fuente_revision. |
| DR | CALIFICACIÓN REGISTRAL..2 | 0 | DOCUMENTAR | documentar | `observacion/importacion_excel` | `valor_fuente` | Si | No | Si | No | Campo no estructurado; preservar durante migración para conciliación. |
| DS | CONVENIO INSCRITO EN EL RAN (FECHA).. | 0 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| DT | SUPERFICIE TOTAL REAL AFECTADA (HA) | 2 | PERSISTIR | persistir | `afectacion` | `superficie_afectada_ha` | Si | No | No | No | Dato administrativo capturado; no ST_Area oficial. |
| DU | ASAMBLEA  1A CONVOCATORIA (FECHA)2 | 8 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |
| DV | ASAMBLEA  2A CONVOCATORIA (FECHA)3 | 3 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |
| DW | ASAMBLEA  REALIZADA (FECHA)24 | 6 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |
| DX | INGRESADO AL RAN (FECHA)25 | 3 | PERSISTIR | persistir | `asamblea` | `fecha_ingreso_ran` | Si | No | No | No | RAN del acta, separado del RAN del convenio. |
| DY | NÚMERO DE SOLICITUD DE INGRESO26 | 3 | PERSISTIR | persistir | `asamblea` | `numero_solicitud_ran` | Si | No | No | No | Solicitud RAN del acta, separada del convenio. |
| DZ | CALIFICACIÓN REGISTRAL.7 | 0 | DOCUMENTAR | documentar | `observacion/importacion_excel` | `valor_fuente` | Si | No | Si | No | Campo no estructurado; preservar durante migración para conciliación. |
| EA | ACTA INSCRITA EN EL RAN (FECHA)38 | 2 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |
| EB | ESTATUS (COMPLETO, PENDIENTE, PROGRAMADO) | 4 | PERSISTIR | persistir | `indemnizacion` | `estatus` | Si | No | No | No | No equivale a pago; pago es hecho financiero separado. |
| EC | ENTREGA DE EXPEDIENTE SICT - PROCURADURÍA AGRARIA | 0 | DOCUMENTAR | documentar | `ninguna` | `campo_reservado` | No | No | No | No | Sin datos en auditoría local; no crear módulo hasta confirmar uso. |
| ED | EXPROPIACIÓN DIRECTA | 1 | PERSISTIR | persistir | `afectacion/proyecto_nucleo` | `expropiacion_directa` | Si | No | No | No | Condición, no salida terminal global automática. |
| EE | EL PROYECTO FERROVIARIO NO AFECTA TIERRAS DE USO COMÚN | 3 | PERSISTIR | persistir | `afectacion/proyecto_nucleo` | `no_afecta_uso_comun/no_afecta_parcelas` | Si | No | No | No | Puede excluir una ruta sin bloquear automáticamente las demás. |
| EF | COMUNIDAD INDÍGENA | 9 | PERSISTIR | persistir | `nucleo_agrario/proyecto_nucleo` | `comunidad_indigena` | Si | No | No | No | Condición de tratamiento; no terminalidad global automática. |
| EG | NO. DE OFICIO FIFONAFE A DGAOPR/REPRESENTACIÓN Y FECHA | 43 | PERSISTIR | persistir | `tramite_fifonafe` | `cuatro_oficios_fechas_resultado_estatus` | Si | No | No | No | Conservar oficio FIFONAFE, oficio DGAOPR, respuesta Representación y respuesta final. |
| EH | NO. DE OFICIO DGAOPR A REPRESENTACIÓN Y FECHA | 24 | PERSISTIR | persistir | `tramite_fifonafe` | `cuatro_oficios_fechas_resultado_estatus` | Si | No | No | No | Conservar oficio FIFONAFE, oficio DGAOPR, respuesta Representación y respuesta final. |
| EI | RESPUESTA REPRESENTACIÓN A DGAOPR NO. DE OFICIO Y FECHA | 43 | PERSISTIR | persistir | `tramite_fifonafe` | `cuatro_oficios_fechas_resultado_estatus` | Si | No | No | No | Conservar oficio FIFONAFE, oficio DGAOPR, respuesta Representación y respuesta final. |
| EJ | RESPUESTA DGAOPR/REPRESENTACIÓN A FIFONAFE NO. DE OFICIO Y FECHA | 24 | PERSISTIR | persistir | `tramite_fifonafe` | `cuatro_oficios_fechas_resultado_estatus` | Si | No | No | No | Conservar oficio FIFONAFE, oficio DGAOPR, respuesta Representación y respuesta final. |
| EK | OBSERVACIONES / ACUERDOS | 1 | PERSISTIR | persistir | `observacion/documento_soporte` | `observaciones` | Si | No | No | No | Preservar texto literal; estructurar sólo si hay ciclo de vida propio. |
| EL | VALIDACIÓN PA/SICT | 0 | DOCUMENTAR | documentar | `ninguna` | `campo_reservado` | No | No | No | No | Sin datos en auditoría local; no crear módulo hasta confirmar uso. |
| EM | OFICIO RAN  PARCELAS CON AFECTACIÓN | 39 | REFERENCIA | referencia | `documento_soporte` | `referencia_oficio_ran_parcelas` | Si | No | Si | No | Referencia documental asociada a parcelas/afectaciones. |
| EN | OBSERVACIONES | 61 | PERSISTIR | persistir | `observacion/documento_soporte` | `observaciones` | Si | No | No | No | Preservar texto literal; estructurar sólo si hay ciclo de vida propio. |
| EO | SOPORTE DOCUMENTAL | 105 | PERSISTIR | persistir | `documento_soporte` | `descripcion/archivo/referencia` | Si | No | No | No | Soporte documental de la fuente. |

## `Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx` - `ORV`

Clasificación: **A. FUENTE DETALLADA**. Fuente detallada de ORV, padron y soporte documental por núcleo.

| Col. | Columna fuente | Filas con dato | Estado | Tipo de tratamiento | Entidad destino | Campo destino | Persiste | Deriva | Referencia | Requiere decisión | Observación |
|---:|---|---:|---|---|---|---|---:|---:|---:|---:|---|
| A | NUM. | 75 | DOCUMENTAR | documentar | `importacion_excel` | `source_row/source_index` | Si | No | Si | No | Identificador de conciliación de fuente; no es entidad de negocio. |
| B | ENTIDAD | 75 | PERSISTIR | persistir | `entidad_federativa` | `nombre/clave` | Si | No | No | No | Resolver catalogo territorial. |
| C | MUNICIPIO | 75 | PERSISTIR | persistir | `municipio` | `nombre/clave_inegi` | Si | No | No | No | Resolver catalogo territorial. |
| D | NÚCLEO AGRARIO | 75 | PERSISTIR | persistir | `nucleo_agrario` | `nombre` | Si | No | No | No | Crear o resolver núcleo dentro del contexto de proyecto. |
| E | E/C | 74 | PERSISTIR | persistir | `nucleo_agrario` | `tipo_nucleo` | Si | No | No | No | Normalizar E/C a ejido/comunidad. |
| F | COMISARIADO_PRESIDENTE | 0 | PERSISTIR | persistir | `orv` | `vigencia/integrantes/acta_eleccion_inscrita_ran` | Si | No | No | No | Datos de órganos de representación y vigilancia. |
| G | COMISARIADO_SECRETARIO | 0 | PERSISTIR | persistir | `orv` | `vigencia/integrantes/acta_eleccion_inscrita_ran` | Si | No | No | No | Datos de órganos de representación y vigilancia. |
| H | COMISARIADO_TESORERO | 0 | PERSISTIR | persistir | `orv` | `vigencia/integrantes/acta_eleccion_inscrita_ran` | Si | No | No | No | Datos de órganos de representación y vigilancia. |
| I | CONSEJO_VIGILANCIA_PRESIDENTE | 0 | PERSISTIR | persistir | `orv` | `vigencia/integrantes/acta_eleccion_inscrita_ran` | Si | No | No | No | Datos de órganos de representación y vigilancia. |
| J | CONSEJO_VIGILANCIA_SECRETARIO1 | 0 | PERSISTIR | persistir | `orv` | `vigencia/integrantes/acta_eleccion_inscrita_ran` | Si | No | No | No | Datos de órganos de representación y vigilancia. |
| K | CONSEJO_VIGILANCIA_SECRETARIO2 | 0 | PERSISTIR | persistir | `orv` | `vigencia/integrantes/acta_eleccion_inscrita_ran` | Si | No | No | No | Datos de órganos de representación y vigilancia. |
| L | FECHA DE PADRÓN | 66 | PERSISTIR | persistir | `padron_historial` | `fecha_padron` | Si | No | No | No | Historial del padrón del núcleo. |
| M | PADRÓN: NÚMERO DE EJIDATARIOS/ COMUNEROS | 45 | PERSISTIR | persistir | `padron_historial` | `numero_ejidatarios_comuneros` | Si | No | No | No | Dato de padrón del núcleo. |
| N | ORV VIGENTES (SI/NO) ESTATUS | 74 | PERSISTIR | persistir | `orv` | `vigencia/integrantes/acta_eleccion_inscrita_ran` | Si | No | No | No | Datos de órganos de representación y vigilancia. |
| O | FECHA DE VENCIMIENTO DE ORV | 74 | PERSISTIR | persistir | `orv` | `vigencia/integrantes/acta_eleccion_inscrita_ran` | Si | No | No | No | Datos de órganos de representación y vigilancia. |
| P | ACTA DE ELECCIÓN DE ORV INSCRITA EN EL RAN (SI/NO) | 68 | PERSISTIR | persistir | `orv` | `vigencia/integrantes/acta_eleccion_inscrita_ran` | Si | No | No | No | Datos de órganos de representación y vigilancia. |
| Q | OBSERVACIONES | 1 | PERSISTIR | persistir | `observacion/documento_soporte` | `observaciones` | Si | No | No | No | Preservar texto literal; estructurar sólo si hay ciclo de vida propio. |
| R | SOPORTE DOCUMENTAL | 75 | PERSISTIR | persistir | `documento_soporte` | `descripcion/archivo/referencia` | Si | No | No | No | Soporte documental de la fuente. |

## `Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx` - `ASAMBLEAS PENDIENTES`

Clasificación: **A. FUENTE DETALLADA**. Fuente detallada/control de asambleas pendientes y excepciones; se concilia con INFORME M-Q.

| Col. | Columna fuente | Filas con dato | Estado | Tipo de tratamiento | Entidad destino | Campo destino | Persiste | Deriva | Referencia | Requiere decisión | Observación |
|---:|---|---:|---|---|---|---|---:|---:|---:|---:|---|
| A | NUM. | 75 | DOCUMENTAR | documentar | `importacion_excel` | `source_row/source_index` | Si | No | Si | No | Identificador de conciliación de fuente; no es entidad de negocio. |
| B | ENTIDAD | 75 | PERSISTIR | persistir | `entidad_federativa` | `nombre/clave` | Si | No | No | No | Resolver catalogo territorial. |
| C | MUNICIPIO | 75 | PERSISTIR | persistir | `municipio` | `nombre/clave_inegi` | Si | No | No | No | Resolver catalogo territorial. |
| D | RESIDENCIA | 75 | PERSISTIR | persistir | `proyecto_nucleo` | `residencia` | Si | No | No | No | Dato del seguimiento del núcleo dentro del proyecto. |
| E | CONSECUTIVO | 75 | PERSISTIR | persistir | `proyecto_nucleo` | `consecutivo` | Si | No | No | No | Consecutivo operativo por proyecto/núcleo. |
| F | NÚCLEO AGRARIO | 75 | PERSISTIR | persistir | `nucleo_agrario` | `nombre` | Si | No | No | No | Crear o resolver núcleo dentro del contexto de proyecto. |
| G | E/C | 74 | PERSISTIR | persistir | `nucleo_agrario` | `tipo_nucleo` | Si | No | No | No | Normalizar E/C a ejido/comunidad. |
| H | NOMBRE DE LA PERSONA ORGANIZADORA AGRARIA RESPONSABLE | 51 | PERSISTIR | persistir | `proyecto_nucleo` | `responsable_nombre` | Si | No | No | No | Responsable operativo. |
| I | DATOS DE CONTACTO (TELÉFONO) | 48 | PERSISTIR | persistir | `proyecto_nucleo` | `responsable_contacto` | Si | No | No | No | Telefono/contacto operativo. |
| J | DESTINO DE LA SUPERFICIE | 38 | PERSISTIR | persistir | `afectacion_colectiva` | `destino_superficie` | Si | No | No | No | Permite TUC, parcela escolar, UAIM, canal, derecho de paso, solares u otro. |
| K | NO. DE PARCELA/SOLAR | 1 | REFERENCIA | referencia | `afectacion_colectiva` | `referencia_parcela_solar` | Si | No | Si | No | Colectivo no exige parcela; se conserva referencia si existe. |
| L | FECHA DE PADRÓN | 14 | PERSISTIR | persistir | `padron_historial` | `fecha_padron` | Si | No | No | No | Historial del padrón del núcleo. |
| M | PADRÓN: NÚMERO DE EJIDATARIOS/ COMUNEROS | 14 | PERSISTIR | persistir | `padron_historial` | `numero_ejidatarios_comuneros` | Si | No | No | No | Dato de padrón del núcleo. |
| N | ORV VIGENTES (SI/NO) | 74 | PERSISTIR | persistir | `orv` | `vigencia/integrantes/acta_eleccion_inscrita_ran` | Si | No | No | No | Datos de órganos de representación y vigilancia. |
| O | FECHA DE VENCIMIENTO DE ORV | 75 | PERSISTIR | persistir | `orv` | `vigencia/integrantes/acta_eleccion_inscrita_ran` | Si | No | No | No | Datos de órganos de representación y vigilancia. |
| P | ACTA DE ELECCIÓN DE ORV INSCRITA EN EL RAN (SI/NO) | 49 | PERSISTIR | persistir | `orv` | `vigencia/integrantes/acta_eleccion_inscrita_ran` | Si | No | No | No | Datos de órganos de representación y vigilancia. |
| Q | CLAVE DEL TRAMO | 0 | REFERENCIA | referencia | `proyecto_nucleo` | `clave_tramo_referencia` | Si | No | Si | No | Referencia histórica opcional; no crea entidad Tramo. |
| R | NÚMERO DE TRAMO | 0 | REFERENCIA | referencia | `proyecto_nucleo` | `numero_tramo_referencia` | Si | No | Si | No | Referencia histórica opcional; no crea entidad Tramo. |
| S | REUNIÓN PROGRAMADA (FECHA) | 62 | PERSISTIR | persistir | `actividad_campo` | `sensibilizacion.fecha_programada_o_realizada` | Si | No | No | No | Actividad del proyecto_nucleo o del contexto de convenio adicional. |
| T | PROGRAMADA POR NA | 62 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| U | REUNIÓN REALIZADA (FECHA) | 62 | PERSISTIR | persistir | `actividad_campo` | `sensibilizacion.fecha_programada_o_realizada` | Si | No | No | No | Actividad del proyecto_nucleo o del contexto de convenio adicional. |
| V | REALIZADA POR NA | 62 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| W | TRIMESTRE | 62 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| X | PROGRAMADO (FECHA) | 62 | PERSISTIR | persistir | `actividad_campo` | `caminamiento.fecha_programada_o_realizada` | Si | No | No | No | Actividad administrativa; no calcula superficie oficial. |
| Y | PROGRAMADO POR NA | 62 | DOCUMENTAR | documentar | `observacion/importacion_excel` | `valor_fuente` | Si | No | Si | No | Campo no estructurado; preservar durante migración para conciliación. |
| Z | REALIZADO (FECHA) | 61 | PERSISTIR | persistir | `actividad_campo` | `caminamiento.fecha_programada_o_realizada` | Si | No | No | No | Actividad administrativa; no calcula superficie oficial. |
| AA | REALIZADO POR NA | 61 | DOCUMENTAR | documentar | `observacion/importacion_excel` | `valor_fuente` | Si | No | Si | No | Campo no estructurado; preservar durante migración para conciliación. |
| AB | MES A CONTAR4 | 61 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| AC | ASAMBLEA  PROGRAMADA 1/a (FECHA) | 50 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |
| AD | ASAMBLEA  PROGRAMADA 2/a (FECHA) | 33 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |
| AE | PROGRAMADA POR NA2 | 44 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| AF | ASAMBLEA  REALIZADA (FECHA) | 42 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |
| AG | REALIZADA POR NA2 | 41 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| AH | MES A CONTAR6 | 40 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| AI | FECHA PROGRAMADA DE INGRESO AL RAN | 0 | PERSISTIR | persistir | `asamblea` | `fecha_programada_ingreso_ran` | Si | No | No | No | RAN del acta. |
| AJ | INGRESADO AL RAN (FECHA) | 20 | PERSISTIR | persistir | `asamblea` | `fecha_ingreso_ran` | Si | No | No | No | RAN del acta, separado del RAN del convenio. |
| AK | INGRESO POR NA | 19 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| AL | MES A CONTAR7 | 19 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| AM | NÚMERO DE SOLICITUD DE INGRESO | 18 | PERSISTIR | persistir | `asamblea` | `numero_solicitud_ran` | Si | No | No | No | Solicitud RAN del acta, separada del convenio. |
| AN | ACTA INSCRITA EN EL RAN (FECHA) | 15 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |
| AO | IINSCRITO POR NA | 14 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| AP | MES A CONTAR8 | 14 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| AQ | ACTA COMPLEMENTARIA | 0 | DOCUMENTAR | documentar | `observacion/importacion_excel` | `valor_fuente` | Si | No | Si | No | Campo no estructurado; preservar durante migración para conciliación. |
| AR | CALIFICACIÓN REGISTRAL | 3 | DOCUMENTAR | documentar | `observacion/importacion_excel` | `valor_fuente` | Si | No | Si | No | Campo no estructurado; preservar durante migración para conciliación. |
| AS | ACUSE FIFONAFE (FECHA) | 0 | PERSISTIR | persistir | `tramite_fifonafe` | `cuatro_oficios_fechas_resultado_estatus` | Si | No | No | No | Conservar oficio FIFONAFE, oficio DGAOPR, respuesta Representación y respuesta final. |
| AT | AVALÚO MAESTRO (INDAABIN) $ | 11 | PERSISTIR | persistir | `afectacion` | `avaluo_monto` | Si | No | No | No | Campo simple; institucion INDAABIN cuando corresponda. |
| AU | FECHA PROGRAMADA PARA FIRMA DE CONVENIO | 4 | PERSISTIR | persistir | `convenio` | `fecha_programada_firma` | Si | No | No | No | Separada de ingreso RAN programado. |
| AV | CONVENIO FIRMADO (FECHA) | 38 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| AW | CONVENIO MONTO 90% | 31 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| AX | CONVENIO MONTO 100% | 33 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| AY | MONTO BDT | 0 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| AZ | MES A CONTAR9 | 38 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| BA | FECHA PROGRAMADA DE INGRESO AL RAN. | 0 | PERSISTIR | persistir | `convenio` | `fecha_programada_ingreso_ran` | Si | No | No | No | Separada de firma programada. |
| BB | INGRESADO AL RAN (FECHA). | 12 | PERSISTIR | persistir | `asamblea` | `fecha_ingreso_ran` | Si | No | No | No | RAN del acta, separado del RAN del convenio. |
| BC | MES A CONTAR10 | 12 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| BD | NÚMERO DE SOLICITUD DE INGRESO. | 12 | PERSISTIR | persistir | `convenio` | `numero_solicitud_ingreso` | Si | No | No | No | Solicitud RAN del convenio; no usar campo_fuente_revision. |
| BE | CONVENIO INSCRITO EN EL RAN (FECHA) | 10 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| BF | MES A CONTAR11 | 10 | DERIVAR | derivar | `dashboard/reporteador` | `periodo_o_conteo_distinto` | No | Si | No | No | Auxiliar de Excel; derivar desde fechas y conteos por núcleo. |
| BG | CONVENIO MODIFICATORIO | 0 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo modificatorio)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| BH | ASAMBLEA  1A CONVOCATORIA (FECHA) | 1 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |
| BI | ASAMBLEA  REALIZADA (FECHA)2 | 1 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |
| BJ | INGRESADO AL RAN (FECHA)2 | 0 | PERSISTIR | persistir | `asamblea` | `fecha_ingreso_ran` | Si | No | No | No | RAN del acta, separado del RAN del convenio. |
| BK | NÚMERO DE SOLICITUD DE INGRESO2 | 0 | PERSISTIR | persistir | `asamblea` | `numero_solicitud_ran` | Si | No | No | No | Solicitud RAN del acta, separada del convenio. |
| BL | ACTA INSCRITA EN EL RAN (FECHA)3 | 0 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |
| BM | ESTATUS (COMPLETO, PENDIENTE, PROGRAMADO) | 0 | PERSISTIR | persistir | `indemnizacion` | `estatus` | Si | No | No | No | No equivale a pago; pago es hecho financiero separado. |
| BN | ENTREGA DE EXPEDIENTE SICT - PROCURADURÍA AGRARIA | 0 | DOCUMENTAR | documentar | `ninguna` | `campo_reservado` | No | No | No | No | Sin datos en auditoría local; no crear módulo hasta confirmar uso. |
| BO | SUPERFICIE TOTAL  PRELIMINAR (HA) | 12 | PERSISTIR | persistir | `afectacion` | `superficie_preliminar_ha` | Si | No | No | No | No colapsar con superficie real afectada. |
| BP | SUPERFICIE TOTAL REAL AFECTADA (HA) | 33 | PERSISTIR | persistir | `afectacion` | `superficie_afectada_ha` | Si | No | No | No | Dato administrativo capturado; no ST_Area oficial. |
| BQ | EXPROPIACIÓN DIRECTA | 5 | PERSISTIR | persistir | `afectacion/proyecto_nucleo` | `expropiacion_directa` | Si | No | No | No | Condición, no salida terminal global automática. |
| BR | EL PROYECTO FERROVIARIO NO AFECTA TIERRAS DE USO COMÚN | 5 | PERSISTIR | persistir | `afectacion/proyecto_nucleo` | `no_afecta_uso_comun/no_afecta_parcelas` | Si | No | No | No | Puede excluir una ruta sin bloquear automáticamente las demás. |
| BS | COMUNIDAD INDÍGENA | 7 | PERSISTIR | persistir | `nucleo_agrario/proyecto_nucleo` | `comunidad_indigena` | Si | No | No | No | Condición de tratamiento; no terminalidad global automática. |
| BT | OBSERVACIONES / ACUERDOS | 0 | PERSISTIR | persistir | `observacion/documento_soporte` | `observaciones` | Si | No | No | No | Preservar texto literal; estructurar sólo si hay ciclo de vida propio. |
| BU | VALIDACIÓN PA/SICT | 0 | DOCUMENTAR | documentar | `ninguna` | `campo_reservado` | No | No | No | No | Sin datos en auditoría local; no crear módulo hasta confirmar uso. |
| BV | OFICIO RAN  PARCELAS CON AFECTACIÓN | 39 | REFERENCIA | referencia | `documento_soporte` | `referencia_oficio_ran_parcelas` | Si | No | Si | No | Referencia documental asociada a parcelas/afectaciones. |
| BW | OBSERVACIONES | 50 | PERSISTIR | persistir | `observacion/documento_soporte` | `observaciones` | Si | No | No | No | Preservar texto literal; estructurar sólo si hay ciclo de vida propio. |
| BX | SOPORTE DOCUMENTAL | 66 | PERSISTIR | persistir | `documento_soporte` | `descripcion/archivo/referencia` | Si | No | No | No | Soporte documental de la fuente. |
| BY | ASAMBLEAS PENDIENTES | 75 | PERSISTIR | persistir | `asamblea` | `fecha_convocatoria/fecha_realizada/resultado` | Si | No | No | No | Acto colectivo y seguimiento RAN del acta. |

## `Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx` - `PCOLECTIVAS`

Clasificación: **C. CONTROL AUXILIAR**. Control auxiliar de COP colectivos por núcleo; contiene permuta y convenio relacionado con dos solares.

| Col. | Columna fuente | Filas con dato | Estado | Tipo de tratamiento | Entidad destino | Campo destino | Persiste | Deriva | Referencia | Requiere decisión | Observación |
|---:|---|---:|---|---|---|---|---:|---:|---:|---:|---|
| A | ENTIDAD | 4 | PERSISTIR | persistir | `entidad_federativa` | `nombre/clave` | Si | No | No | No | Resolver catalogo territorial. |
| B | MUNICIPIO | 4 | PERSISTIR | persistir | `municipio` | `nombre/clave_inegi` | Si | No | No | No | Resolver catalogo territorial. |
| C | NÚCLEO AGRARIO | 5 | PERSISTIR | persistir | `nucleo_agrario` | `nombre` | Si | No | No | No | Crear o resolver núcleo dentro del contexto de proyecto. |
| D | TOTAL DE COPS | 0 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| E | FECHA PROGRAMADA PARA FIRMA | 2 | PERSISTIR | persistir | `convenio` | `fecha_programada_firma` | Si | No | No | No | Separada de ingreso RAN programado. |
| F | NO. DE COPS A FIRMAR | 5 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| G | COP FIRMADOS | 5 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| H | SOPORTE DOCUMENTAL | 5 | PERSISTIR | persistir | `documento_soporte` | `descripcion/archivo/referencia` | Si | No | No | No | Soporte documental de la fuente. |
| I | COP INGRESADOS AL RAN | 1 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| J | COP INSCRITOS | 1 | PERSISTIR | persistir | `convenio` | `fecha_firma/montos/ran/superficie (tipo cop_original)` | Si | No | No | No | Normalizar bloques horizontales como filas repetibles de convenio. |
| K | OBSERVACIONES | 4 | PERSISTIR | persistir | `observacion/documento_soporte` | `observaciones` | Si | No | No | No | Preservar texto literal; estructurar sólo si hay ciclo de vida propio. |
| M | Columna M | 2 | DOCUMENTAR | documentar | `dashboard/convenio` | `control_auxiliar_conciliacion` | No | Si | No | No | Control auxiliar; usar para conciliación y excepción, no duplicar totales. |
| N | 11968582.460000001 | 2 | DOCUMENTAR | documentar | `dashboard/convenio` | `control_auxiliar_conciliacion` | No | Si | No | No | Control auxiliar; usar para conciliación y excepción, no duplicar totales. |

## Campos en estado REVISAR

Ninguna columna auditada queda en estado `REVISAR`. Los campos vacíos o auxiliares se clasifican como `DOCUMENTAR`, `DERIVAR` o `NO IMPLEMENTAR`; los casos raros con datos se preservan como observación/modalidad/relación excepcional.

## Casos excepcionales identificados

- `1 COP FIRMADO (PERMUTA)` en `Hoja1` y `PCOLECTIVAS`: tratar como `convenio.tipo_convenio = cop_original` con `modalidad_especial = permuta` y observación literal.
- `1 COP PARA DOS SOLARES, DUDA` en `Hoja1` y `PCOLECTIVAS`: representar con `convenio_afectacion` sólo si la revisión documental confirma que un convenio cubre más de una afectación/superficie; preservar observación.
- Expropiación directa, comunidad indígena y no afectación de uso común: registrar como condiciones sin cierre terminal global automático.
