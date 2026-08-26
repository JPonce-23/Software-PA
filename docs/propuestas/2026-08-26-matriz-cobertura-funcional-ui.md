# Matriz de cobertura funcional UI — esquema 035

Fecha de corte: 2026-08-26. Se auditaron directamente los tres libros locales sin modificarlos. El inventario fila por fila está en [2026-08-26-inventario-columnas-excel.csv](2026-08-26-inventario-columnas-excel.csv) y se reproduce con `backend/scripts/audit_excel_columns.py`.

## Cobertura física

| Archivo | Hoja | Columnas físicas operativas | OK | Derivado | Referencia legacy | No aplica | Decisión pendiente |
|---|---:|---:|---:|---:|---:|---:|---:|
| PROYECTOS VÍAS SEGUIMIENTO GENERAL.xlsx | INFORME GENERAL | 59 | 1 | 58 | 0 | 0 | 0 |
|  | COP´S COLECTIVOS | 61 | 0 | 61 | 0 | 0 | 0 |
|  | INDIVIDUALES | 20 | 1 | 19 | 0 | 0 | 0 |
| SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS-INDIVIDUALES-MQ.xlsx | General | 18 | 16 | 0 | 0 | 1 | 1 |
|  | PROPUESTA | 69 | 55 | 10 | 2 | 1 | 1 |
|  | COP´S PENDIENTES | 40 | 33 | 3 | 2 | 1 | 1 |
|  | Hoja1 | 11 | 3 | 8 | 0 | 0 | 0 |
|  | Hoja2 | 0 | 0 | 0 | 0 | 0 | 0 |
| Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx | General | 18 | 16 | 0 | 0 | 1 | 1 |
|  | INFORME M-Q | 145 | 119 | 22 | 2 | 1 | 1 |
|  | ORV | 18 | 17 | 0 | 0 | 1 | 0 |
|  | ASAMBLEAS PENDIENTES | 77 | 61 | 12 | 2 | 1 | 1 |
|  | PCOLECTIVAS | 11 | 3 | 8 | 0 | 0 | 0 |
| **Total** |  | **547** | **325** | **201** | **8** | **7** | **6** |

No quedan columnas `FALTA_UI`, `FALTA_API`, `FALTA_BACKEND` o `FALTA_MODELO`. Las seis decisiones pendientes son apariciones del mismo encabezado `VALIDACIÓN PA/SICT`: la fuente no define actor, resultado, catálogo ni momento del proceso y no se fuerza dentro de observaciones.

## Correspondencia funcional

| Concepto Excel / documental | Modelo actual | Schema / API | Pantalla y control | Estado |
|---|---|---|---|---|
| Proyecto → Entidad → Municipio → Núcleo → expediente | `proyecto`, catálogos territoriales, `nucleo_agrario`, `proyecto_nucleo` | recursos de proyecto, catálogos y ProyectoNucleo | selectores dependientes y barra de contexto | OK |
| NUM. | orden físico de hoja | no se persiste | no se pide como ID | NO_APLICA |
| Residencia, responsable agrario y teléfono | `proyecto_nucleo` | `ProyectoNucleo` GET/PATCH | General, labels operativos | OK |
| Consecutivo, clave/número de tramo | `proyecto_nucleo_referencia` | referencias GET/POST/PATCH | General · Referencias del tramo | OK / REFERENCIA_LEGACY |
| Seis cargos nominales ORV | `orv_integrante` + `persona` | integrantes GET/POST/PATCH | Comisariado y Consejo de Vigilancia separados | OK |
| Vigencia, vencimiento y acta ORV RAN | `orv` | ORV GET/POST/PATCH | estado visual, fechas y documentos | OK |
| Fecha y número del padrón | `padron_historial` | padrón GET/POST/PATCH | ORV y Padrón, documento vinculado | OK |
| Sensibilización / caminamiento | `actividad_campo` | actividades GET/POST/PATCH | dos bloques diferenciados | OK |
| Trimestre / mes a contar | fecha del hecho y vistas KPI | dashboard | no se captura; se deriva | DERIVADO |
| Programada/realizada por NA | marca repetida sin actor técnico inequívoco | fecha/responsable/resultado de actividad | ayuda de contexto; no se guarda “X” | DERIVADO |
| Destino, situación y condición especial | `afectacion` | afectaciones GET/POST/PATCH | Afectación colectiva / individual | OK |
| Superficie preliminar, real y adicional | `afectacion` / `convenio` | schemas del hecho | controles numéricos en ha | OK |
| Avalúo maestro INDAABIN | `afectacion.avaluo_*` | afectación | monto, fecha, referencia e institución | OK |
| Parcela, PPT, certificado, folio y constancia | `parcela` | parcelas GET/POST/PATCH | Afectación individual | OK |
| Titular nominal | `parcela_titular` + `persona` | titulares GET/POST/PATCH | listado nominal; no muestra IDs | OK |
| Tipo jurídico y motivo de Asamblea | `asamblea.tipo_asamblea` + `contexto_proceso` | Asamblea GET/POST/PATCH | dos selects independientes | OK — migración 035 |
| Convocatorias, celebración, resultado y RAN | `asamblea` | Asamblea GET/POST/PATCH | secciones Convocatorias y Seguimiento RAN | OK |
| COP, modificatorio, superficie adicional, obras, ampliación y remanente | `convenio.tipo_convenio` | convenio transaccional + PATCH | formulario dinámico por ámbito/tipo | OK |
| Firma, 90 %, 100 %, BDT, superficie y RAN del convenio | `convenio` | convenio | secciones Firma/contraprestación y RAN | OK |
| Permuta | `convenio.modalidad_especial` del COP original | convenio | modalidad visible sólo en COP | OK |
| Convenio multiafectación | `convenio_afectacion` | asociación adicional | “Asociar otra afectación” sin IDs | OK |
| Acuse FIFONAFE | `tramite_fifonafe.acuse_fifonafe_fecha` | FIFONAFE GET/POST/PATCH | fecha de acuse | OK — migración 035 |
| Cuatro oficios y fechas | `tramite_fifonafe` | FIFONAFE | secuencia numerada; regla operativa, no legal | OK |
| Afectaciones cubiertas por FIFONAFE | `tramite_fifonafe_afectacion` | alta N:M y asociación | nombres operativos, no IDs | OK |
| Entrega expediente SICT–PA | `indemnizacion.fecha_entrega_expediente_pa` | indemnización GET/POST/PATCH | Indemnización y Pagos | OK — migración 035 |
| Estatus de indemnización | `indemnizacion` | indemnización | estado, programación y resolución | OK |
| Beneficiario, monto, fecha, medio y referencia | `pago` | pagos GET/POST/PATCH | cadena financiera desde afectación | OK |
| Soporte documental | `documento`, `documento_version`, `documento_vinculo` | documentos y versiones | metadatos + versiones inmutables | OK |
| Fecha y número/folio documental | `documento.fecha_documento`, `numero_folio` | Documento GET/POST/PATCH | Documentos | OK — migración 035 |
| Archivo, hoja, fila, columna y tratamiento | `trazabilidad_fuente` | trazabilidad GET/POST | panel de trazabilidad | OK |
| Totales de INFORME GENERAL | `vw_dashboard_kpi` | dashboard KPI/CSV | Dashboard | DERIVADO |
| Geometría | `trazo_proyecto`, núcleo y parcela opcional | GIS/importador | mapa por proyecto | OK; no es gate administrativo |

## Validación jurídica y decisiones

- La Asamblea, comisariado y Consejo de Vigilancia son órganos distintos. El ORV se presenta con cargos nominales y propietarios/suplentes cuando existan.
- La vigencia ordinaria de tres años se usa como información y alerta; prevalecen las fechas capturadas y no se fuerza una suma automática.
- El consentimiento de ocupación previa corresponde a titulares afectados o a la Asamblea tratándose de uso común. Una afectación individual no queda subordinada a Asamblea colectiva.
- El tipo de Asamblea ya no se confunde con el convenio que la motiva: `anuencia`/`retiro_fondos`/`otra` se separa de COP, modificatorio, superficie adicional u obras complementarias.
- Los requisitos del COP se acreditan principalmente mediante el instrumento y sus versiones documentales. El seguimiento conserva superficie, montos, firma e inscripción RAN sin convertir cada cláusula en columna.
- `VALIDACIÓN PA/SICT` queda `DECISION_FUNCIONAL_REQUERIDA` hasta que el área dueña defina responsable, catálogo, evidencia y momento del flujo.

## Exclusiones confirmadas

- No reaparecen `TramoNucleo`, `AfectacionCiclo` ni `usuario_tramo`.
- `ST_Intersects` no autoriza expedientes y `ST_Area` no determina superficies oficiales.
- “Dar de baja” permanece visible y deshabilitado; no ejecuta `DELETE` ni cambia `activo`.
