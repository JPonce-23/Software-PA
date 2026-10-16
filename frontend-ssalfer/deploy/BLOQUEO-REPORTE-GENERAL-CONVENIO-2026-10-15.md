# Reporte general de convenio: interfaz preparada y datos pendientes

Fecha: 15 de octubre de 2026.

## Hallazgo confirmado en el repositorio

Se revisaron las rutas de `backend/app/routers/reporting.py` y sus respuestas en `backend/app/schemas.py`. No existe un reporte que entregue todas las columnas solicitadas relacionadas. No se modificó backend ni se inventó una ruta.

| Reporte actual | Qué entrega | Qué impide usarlo como reporte general |
|---|---|---|
| `/reportes/convenios/valores-declarados` | Identificadores, ámbito, tipo, concepto, unidad, valor declarado, fecha reportada y firma acreditada | Una fila por concepto, sin municipio, nombre de núcleo, parcela ni fechas RAN relacionadas |
| `/reportes/convenios/impactos` | Impactos por convenio/afectación, concepto, efecto, fecha y valor | Su unidad de fila es el impacto, no el convenio/parcela; no contiene el conjunto de fechas y referencias solicitado |
| `/reportes/convenios/impactos-periodo` | Agrupaciones por periodo, ámbito y concepto | Son agregados, no registros individuales para estas hojas |
| `/reportes/convenios/cobertura-impactos` | Universo, clasificados, pendientes y sin firma por proyecto/entidad/concepto | No contiene el detalle documental o territorial |
| `/reportes/convenios/colectivos-destino` (alias `/reportes/convenios/destinos`) | IDs de convenio, núcleo y asamblea, destino, superficies en ha, monto declarado y fecha de firma | No entrega municipio/nombre de núcleo ni las fechas de asamblea y de sus dos trámites RAN. El monto es del instrumento completo, no aditivo por destino |

Los reportes existentes ya admiten `id_entidad` y la pantalla anterior ya tenía un filtro genérico de entidades. Ese catálogo no demuestra qué entidades tienen convenios del proyecto. No se reutilizó como si fuera un filtro de registros existentes.

## Información que debe consolidar backend

La consolidación es viable como una proyección de lectura del servidor, pero requiere acordar su contrato y las reglas siguientes. Esto es una propuesta de datos, no un endpoint implementado.

1. Proyecto autorizado; ID y nombre de entidad; municipio; ID del vínculo proyecto-núcleo y nombre del núcleo.
2. Convenio identificado de forma estable, ámbito individual/colectivo y tipo. Aclarar si «TIPO DE CONVENIO» usa el tipo jurídico o el tipo COP operativo: la referencia muestra «ORIGEN» y no deben confundirse los dos conceptos.
3. Individuales: número de parcela como texto, vínculo con la afectación/convenio y superficie correspondiente en m². Definir qué fila producir cuando un convenio ampara varias parcelas, sin repetir superficies o dinero como si fueran importes adicionales.
4. Firma de COP y trámite RAN del convenio: fechas de ingreso e inscripción, procedentes de sus eventos pertinentes. No sustituirlas por fecha de actualización, programación o un estado textual.
5. Colectivos: destino de superficie, superficie en m², asamblea relacionada y fecha de realización; ingreso e inscripción del trámite RAN de esa asamblea; firma, ingreso e inscripción del convenio en campos independientes.
6. Montos declarados 90% y 100% separados y con moneda/unidad explícitas. No calcular el 90% a partir del 100%, no sustituirlos por pagos o impactos, ni sumar el monto de un convenio repetido en varios destinos/parcelas.
7. Regla determinista cuando haya varias asambleas, trámites, reingresos o inscripciones; no elegir una fecha por su posición en una lista.
8. Mantener ausencias como nulos y ceros reales como ceros. Definir tratamiento de bajas, convenios sustituidos y firmas pendientes. No completar fechas o importes faltantes con inferencias.
9. Estados disponibles del proyecto derivados del universo completo de ambas hojas, antes del filtro de entidad. El mismo filtro debe aplicarse a individuales y colectivos. No restringir la lista a la primera página ni al subconjunto individual.
10. Paginación/total o exportación completa y orden estable; alcance y permisos de lectura iguales a los reportes actuales. Si hay varias páginas, ambas hojas deben provenir de un mismo corte consistente.

## Entrega frontend de esta ronda

- Nueva pestaña «Reporte general de convenio», con ícono, `role="tab"`, `aria-selected` y `data-reporte="general"`.
- Proyecto y selector «Estado» con «Todos los estados». Estado permanece deshabilitado: no se publican opciones inventadas ni se confunde el catálogo completo con entidades que tienen registros.
- Se reutilizan `theadReportesConvenios` y `tbodyReportesConvenios` para mostrar las 12 columnas de individuales y el aviso de datos pendientes. La nota aclara que el Excel incluirá colectivos.
- Consulta, búsqueda, paginación de resultados y exportación Excel no operan mientras falte el contrato. La ausencia de datos consolidados no se presenta como «cero convenios».
- No hay consultas por convenio para construir este reporte. Una respuesta pendiente de otra pestaña no sobrescribe la nueva vista.
- Las otras cuatro pestañas conservan sus definiciones de filtros, columnas, endpoints y exportación CSV.

**La exportación nativa desde el navegador queda pendiente**, junto con su biblioteca cliente de XLSX. No se añadió una dependencia sin uso a la pantalla bloqueada. El archivo de prueba adjunto se generó fuera de la aplicación con la herramienta de hojas de cálculo; no constituye una descarga del backend ni una exportación real del proyecto.

## Archivo de prueba y evidencias

- [Excel de prueba](../../outputs/convenios-general-2026-10-15/Reporte-general-convenio-PRUEBA.xlsx): datos ficticios rotulados, sin copiar registros reales de la referencia. Hojas «Convenios individuales» y «Convenios colectivos». Cada una tiene 12 columnas; individuales incorpora los montos 90% y 100%. Colectivos conserva ambos pares de «INGRESO AL RAN (FECHA)» e «INSCRITO AL RAN (FECHA)», con rótulos superiores para distinguir asamblea y convenio.
- [Captura de la pestaña](../../outputs/convenios-general-2026-10-15/pestana-reporte-general.png).
- Las columnas se cotejaron con el archivo de referencia `DOC-20261015-WA0038.xlsx`, fila 3 de ambas hojas. No se modificó el original.

## Verificación realizada

Prueba automatizada en Edge (`qa-reporte-general-convenio-2026-10-15.cjs`) con API simulada: pestaña nueva, proyecto de contexto, selector de estado sin opciones inventadas, 12 encabezados, consulta/exportación bloqueadas, ausencia de solicitudes desde la nueva pestaña, descarte de respuesta atrasada y vuelta a las cuatro pestañas anteriores con consulta y CSV. Sin errores JavaScript. No se hicieron escrituras a datos reales.

Excel reabierto con un lector independiente: dos hojas, columnas correctas, encabezados RAN repetidos preservados, fechas tipadas, superficies y montos numéricos, identificadores con ceros iniciales y ausencias sin convertir a cero. Se revisaron visualmente las dos hojas. No se verificó en Microsoft Excel de escritorio.

Sin cambios de backend, commit ni push. Los cambios locales de rondas anteriores se conservaron.
