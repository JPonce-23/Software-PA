# Cierre Excel V1 — bloque 02

Estado: implementado y validado en QA; **el bloque no se declara cerrado**.

Alcance: expropiación directa, TUC, comunidad y consulta indígena, suspensión,
reapertura y cambio de alcance. No incluye una regla especial de
`juicio_agrario` sobre ORV ni modifica el esquema publicado 001–006.

## Evidencia aplicada

| Caso | Archivo / hoja / fila | Regla verificada |
|---|---|---|
| Expropiación directa | `Copia de SEGUIMIENTO... (REV) MQ.xlsx`, `ASAMBLEAS PENDIENTES`, filas 8, 23, 49, 52 y 62 | La condición vigente se cuenta por núcleo distinto; no implica cierre, decreto ni no-TUC. |
| ORV especial | `Copia de SEGUIMIENTO... (REV) MQ.xlsx`, `INFORME M-Q`, fila 10, AHORCADO | Se conserva como evento `otro`, objetivo ORV, detalle y documento. No se inventa fecha ni suspensión. |
| Cambio no-TUC a TUC | REV, `INFORME M-Q`, fila 27, y `Copia SEGUIMIENTO...MEET 27082026.xlsx`, `INFORME M-Q`, fila 33, SANTA MARÍA HUECATITLA | `afecta_tuc=false→true` conserva ProyectoNucleo e historia; el cambio usa la fecha documentada de asamblea `24/04/2026`. |
| Comunidad indígena | Archivo 27/08, `INFORME M-Q`, fila 20, SAN CLEMENTE | `comunidad_indigena=true` no crea consulta, suspensión ni estado funcional. |
| Consulta sin año | Archivo 27/08, `INFORME M-Q`, fila 20 | Se conserva el evento sin fecha; no aparece en un periodo inventado. |
| Cambio de alcance | Archivo 27/08, `INFORME M-Q`, fila 80, SAN PEDRITO ALPUYECA | La reunión `03/02/2026` acredita necesidad de nuevo caminamiento, no caminamiento realizado. |
| Contradicción TUC | Archivo 27/08, `INFORME M-Q`, fila 32, SANTA BÁRBARA | `afecta_tuc=NULL`, `tuc_revision_pendiente=true` y detalle de revisión; no se cuenta como no-TUC. |

## Indicador de expropiación actual

`GET /api/reportes/resumen-actual` incorpora
`expropiacion_directa_actual` en la capa de lectura. La fuente es exclusivamente
el valor actual `afectacion.condicion_especial='expropiacion_directa'` de
afectaciones activas asociadas a ProyectoNucleo y núcleo activos.

El indicador:

- cuenta `DISTINCT id_proyecto_nucleo`;
- no usa eventos históricos de seguimiento;
- no deriva cierre, decreto, suspensión ni valor de `afecta_tuc`;
- desaparece cuando ninguna afectación activa del núcleo conserva actualmente
  esa condición;
- respeta los filtros y permisos ya existentes de resumen actual.

La vigencia disponible es la del valor actual de la afectación y su baja lógica.
No se ofrece una serie histórica de la condición; la auditoría técnica permanece
en bitácora y no se convierte artificialmente en una fecha funcional.

## Validación ejecutada

Entorno comprobado: `APP_ENV=test`, `DB_NAME=software_pa_test`,
`TEST_ALLOW_DATABASE=software_pa_test`. El proceso verificó con una consulta
real que `current_database()` era `software_pa_test`. El ledger y los checksums
coincidieron exactamente con los archivos 001–006 del HEAD.

Resultados del 7 de septiembre de 2026:

- regresión nueva: `8 passed` en `5.28s`;
- 002 + 004 + 005 + 006 + bloque 02: `68 passed` en `39.77s`;
- advertencias: deprecación TestClient/httpx y reescritura de `anyio`; ninguna
  afecta el resultado funcional.

Las pruebas se ejecutaron desde un contenedor efímero con el código montado en
modo sólo lectura y credenciales temporales de un administrador exclusivo de QA.
No se restauró el golden ni se ejecutaron pruebas contra `db_pruebas_alfredo`.

## Pendiente deliberado

- `juicio_agrario` sobre ORV colectivo no se implementa. Hasta una decisión de
  dominio posterior, se registra como caso especial `otro`, con objetivo ORV,
  detalle y documento.
- Una reunión posterior no equivale a reapertura. Sólo un evento explícito
  `reapertura`, con fecha y detalle, cambia el estado.
- Una comunidad indígena no equivale a consulta iniciada o realizada.
- Las actuaciones sin año completo permanecen sin fecha y fuera del reporte
  temporal.
- No se añadieron estados de consulta, tablas, columnas, endpoints ni catálogos.
