# Matriz de trazabilidad — Excel → modelo objetivo

> **Fecha:** 2026-08-24  
> **Alcance:** hojas `PROPUESTA` (individual) e `INFORME M-Q` (colectivo), más contraste con la estructura fuente.

## 1. Criterio

La columna `Filas con dato` indica presencia en la muestra auditada, no obligatoriedad jurídica. Una columna vacía no se elimina automáticamente: se clasifica como `REVISIÓN` cuando necesita confirmación funcional.

Tratamientos principales: `MAESTRO`, `PROYECTO_NUCLEO`, `ACTIVIDAD`, `PARCELA`, `AFECTACIÓN COLECTIVA`, `ASAMBLEA`, `CONVENIO`, `RAN`, `FIFONAFE`, `INDEMNIZACIÓN`, `DOCUMENTO`, `DERIVADO`, `REFERENCIA`, `REVISIÓN`.

## 2. Derechos individuales — hoja `PROPUESTA`

| # | Columna Excel | Filas con dato (683) | Tratamiento | Destino objetivo | Nota |
|---:|---|---:|---|---|---|
| 1 | NUM. | 683 | MIGRACIÓN | `importacion.source_row` | Índice de fila de origen; no es entidad de negocio. |
| 2 | ENTIDAD | 683 | MAESTRO | `nucleo_agrario → municipio → entidad_federativa` | Resolver por catálogo; no duplicar texto si hay FK. |
| 3 | MUNICIPIO | 683 | MAESTRO | `nucleo_agrario.id_municipio` | Resolver por catálogo. |
| 4 | RESIDENCIA | 683 | PROYECTO_NUCLEO | `proyecto_nucleo.residencia` | Dato del seguimiento del núcleo dentro del proyecto. |
| 5 | CONSECUTIVO | 683 | PROYECTO_NUCLEO | `proyecto_nucleo.consecutivo` | Consecutivo operativo de seguimiento. |
| 6 | NÚCLEO AGRARIO | 683 | MAESTRO | `nucleo_agrario.nombre_nucleo` | Resolver/crear maestro y relación proyecto_nucleo. |
| 7 | E/C | 683 | MAESTRO | `nucleo_agrario.tipo_nucleo` | Normalizar E→ejido, C→comunidad. |
| 8 | NOMBRE DE LA PERSONA ORGANIZADORA AGRARIA RESPONSABLE | 571 | PROYECTO_NUCLEO | `proyecto_nucleo.responsable_nombre` | Responsable operativo por proyecto. |
| 9 | DATOS DE CONTACTO (TELÉFONO) | 500 | PROYECTO_NUCLEO | `proyecto_nucleo.responsable_telefono` | Contacto operativo. |
| 10 | TIPO DE PARCELA (INDIVIDUAL) | 655 | PARCELA | `parcela.tipo_parcela` | Tipo de parcela. |
| 11 | NO. DE PARCELA | 310 | PARCELA | `parcela.no_parcela` | Número de parcela de fuente. |
| 12 | NO. DE PARCELA PPT | 657 | PARCELA | `parcela.no_parcela_ppt` | Número PPT. |
| 13 | NOMBRE DE LA PERSONA TITULAR DE LA PARCELA | 683 | TITULAR | `persona + parcela_titular` | Normalizar persona; conservar literal fuente para conciliación. |
| 14 | CONSTANCIA DE VIGENCIA DE DERECHOS (FECHA) | 454 | PARCELA | `parcela.constancia_vigencia_fecha` | Fecha de constancia. |
| 15 | CERTIFICADO PARCELARIO | 565 | PARCELA | `parcela.certificado_parcelario` | Certificado. |
| 16 | FOLIO DE DERECHOS | 378 | PARCELA | `parcela.folio_derechos` | Folio. |
| 17 | CLAVE DEL TRAMO | 567 | REFERENCIA | `proyecto_nucleo.clave_tramo_referencia NULL` | Referencia histórica; no requiere entidad Tramo. |
| 18 | NÚMERO DE TRAMO | 0 | REFERENCIA | `proyecto_nucleo.numero_tramo_referencia NULL` | Referencia histórica; no requiere entidad Tramo. |
| 19 | CONVENIO FIRMADO (FECHA) | 460 | CONVENIO | `convenio[cop_original].fecha_firma` | Normalizar como fila de convenio. |
| 20 | CONVENIO MONTO 90% | 290 | CONVENIO | `convenio[cop_original].monto_90` | Normalizar como fila de convenio. |
| 21 | CONVENIO MONTO 100% | 445 | CONVENIO | `convenio[cop_original].monto_100` | Normalizar como fila de convenio. |
| 22 | MONTO BDT | 10 | CONVENIO | `convenio[cop_original].monto_bdt` | Normalizar como fila de convenio. |
| 23 | TRIMESTRE | 460 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 24 | CONVENIO INGRESADO AL RAN (FECHA) | 407 | CONVENIO | `convenio[cop_original].ingreso_ran_fecha` | Normalizar como fila de convenio. |
| 25 | NO. DE SOLICITUD DE INGRESO | 407 | CONVENIO | `convenio[cop_original].campo_fuente_revision` | Normalizar como fila de convenio. |
| 26 | TRIMESTRE2 | 407 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 27 | CALIFICACIÓN REGISTRAL | 81 | CONVENIO | `convenio[cop_original].calificacion_registral` | Normalizar como fila de convenio. |
| 28 | CONVENIO INSCRITO EN EL RAN (FECHA) | 345 | CONVENIO | `convenio[cop_original].convenio_inscrito_fecha_ran` | Normalizar como fila de convenio. |
| 29 | TRIMESTRE22 | 345 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 30 | SUPERFICIE TOTAL (HA). | 434 | CONVENIO | `convenio[cop_original].superficie_ha` | Normalizar como fila de convenio. |
| 31 | CONVENIO MODIFICATORIO (FECHA) | 1 | CONVENIO | `convenio[modificatorio].fecha_firma` | Normalizar como fila de convenio. |
| 32 | CONVENIO MONTO 90%2 | 0 | CONVENIO | `convenio[modificatorio].monto_90` | Normalizar como fila de convenio. |
| 33 | CONVENIO MONTO 100% 2 | 1 | CONVENIO | `convenio[modificatorio].monto_100` | Normalizar como fila de convenio. |
| 34 | TRIMESTRE4 | 1 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 35 | CONVENIO AMPLIACIÓN (FECHA) | 118 | CONVENIO | `convenio[ampliacion].fecha_firma` | Normalizar como fila de convenio. |
| 36 | CONVENIO MONTO 90%.. | 77 | CONVENIO | `convenio[ampliacion].monto_90` | Normalizar como fila de convenio. |
| 37 | CONVENIO MONTO 100% .. | 118 | CONVENIO | `convenio[ampliacion].monto_100` | Normalizar como fila de convenio. |
| 38 | MONTO BDT2 | 18 | CONVENIO | `convenio[ampliacion].monto_bdt` | Normalizar como fila de convenio. |
| 39 | TRIMESTRE3 | 119 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 40 | CONVENIO INGRESADO AL RAN (FECHA)2 | 57 | CONVENIO | `convenio[ampliacion].ingreso_ran_fecha` | Normalizar como fila de convenio. |
| 41 | NO. DE SOLICITUD DE INGRESO3 | 57 | CONVENIO | `convenio[ampliacion].campo_fuente_revision` | Normalizar como fila de convenio. |
| 42 | TRIMESTRE24 | 57 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 43 | CALIFICACIÓN REGISTRAL2 | 0 | CONVENIO | `convenio[ampliacion].calificacion_registral` | Normalizar como fila de convenio. |
| 44 | CONVENIO INSCRITO EN EL RAN (FECHA)3 | 16 | CONVENIO | `convenio[ampliacion].convenio_inscrito_fecha_ran` | Normalizar como fila de convenio. |
| 45 | TRIMESTRE224 | 16 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 46 | SUPERFICIE DE AMPLIACIÓN | 118 | CONVENIO | `convenio[ampliacion].superficie_ha` | Normalizar como fila de convenio. |
| 47 | CONVENIO AMPLIACIÓN 2 (FECHA). | 3 | CONVENIO | `convenio[ampliacion_remanente].fecha_firma` | Normalizar como fila de convenio. |
| 48 | CONVENIO MONTO 90%..3 | 2 | CONVENIO | `convenio[ampliacion_remanente].monto_90` | Normalizar como fila de convenio. |
| 49 | CONVENIO MONTO 100% ..4 | 3 | CONVENIO | `convenio[ampliacion_remanente].monto_100` | Normalizar como fila de convenio. |
| 50 | MONTO BDT25 | 0 | CONVENIO | `convenio[ampliacion_remanente].monto_bdt` | Normalizar como fila de convenio. |
| 51 | TRIMESTRE36 | 3 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 52 | CONVENIO INGRESADO AL RAN (FECHA)27 | 1 | CONVENIO | `convenio[ampliacion_remanente].ingreso_ran_fecha` | Normalizar como fila de convenio. |
| 53 | NO. DE SOLICITUD DE INGRESO38 | 1 | CONVENIO | `convenio[ampliacion_remanente].campo_fuente_revision` | Normalizar como fila de convenio. |
| 54 | TRIMESTRE249 | 1 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 55 | CALIFICACIÓN REGISTRAL210 | 0 | CONVENIO | `convenio[ampliacion_remanente].calificacion_registral` | Normalizar como fila de convenio. |
| 56 | CONVENIO INSCRITO EN EL RAN (FECHA)311 | 0 | CONVENIO | `convenio[ampliacion_remanente].convenio_inscrito_fecha_ran` | Normalizar como fila de convenio. |
| 57 | TRIMESTRE22412 | 0 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 58 | SUPERFICIE DE AMPLIACIÓN2 | 3 | CONVENIO | `convenio[ampliacion_remanente].superficie_ha` | Normalizar como fila de convenio. |
| 59 | ESTATUS (COMPLETO, PENDIENTE, PROGRAMADO) | 11 | INDEMNIZACIÓN | `indemnizacion.estatus / tramite_fifonafe.estatus` | Estatus administrativo. |
| 60 | ENTREGA DE EXPEDIENTE SICT - PROCURADURÍA AGRARIA. | 0 | REVISIÓN | `expediente_entrega_sict_pa NULL` | Sin datos en muestra; confirmar uso. |
| 61 | NO. DE OFICIO FIFONAFE A DGAOPR/REPRESENTACIÓN Y FECHA | 272 | FIFONAFE | `tramite_fifonafe.oficio_fifonafe_a_dgaopr + fecha` | Separar número y fecha al capturar/importar. |
| 62 | NO. DE OFICIO DGAOPR A REPRESENTACIÓN Y FECHA | 151 | FIFONAFE | `tramite_fifonafe.oficio_dgaopr_a_repr + fecha` | Separar número y fecha al capturar/importar. |
| 63 | RESPUESTA REPRESENTACIÓN A DGAOPR NO. DE OFICIO Y FECHA | 234 | FIFONAFE | `tramite_fifonafe.respuesta_repr_a_dgaopr + fecha` | Separar número y fecha al capturar/importar. |
| 64 | RESPUESTA DGAOPR/REPRESENTACIÓN A FIFONAFE NO. DE OFICIO Y FECHA | 241 | FIFONAFE | `tramite_fifonafe.respuesta_dgaopr_a_fifonafe + fecha` | Separar número y fecha al capturar/importar. |
| 65 | OBSERVACIONES / ACUERDOS | 0 | OBSERVACIÓN | `observaciones / minuta-acuerdo si procede` | Texto fuente; estructurar acuerdos sólo cuando aporte valor. |
| 66 | VALIDACIÓN PA/SICT | 0 | REVISIÓN | `validacion_pa_sict NULL` | Sin datos en muestra; confirmar uso. |
| 67 | OFICIO RAN PARCELAS CON AFECTACIÓN | 52 | RAN | `referencia_oficio_ran_parcelas NULL` | Referencia documental observada en 52 filas. |
| 68 | OBSERVACIONES | 211 | OBSERVACIÓN | `observaciones / minuta-acuerdo si procede` | Texto fuente; estructurar acuerdos sólo cuando aporte valor. |
| 69 | *SOPORTE | 456 | DOCUMENTO | `documentacion_soporte/documento_version` | Conservar evidencia y faltantes. |

## 3. Derechos colectivos — hoja `INFORME M-Q`

| # | Columna Excel | Filas con dato (96) | Tratamiento | Destino objetivo | Nota |
|---:|---|---:|---|---|---|
| 1 | NUM. | 96 | MIGRACIÓN | `importacion.source_row` | Índice de fila de origen; no es entidad de negocio. |
| 2 | ENTIDAD | 96 | MAESTRO | `nucleo_agrario → municipio → entidad_federativa` | Resolver por catálogo; no duplicar texto si hay FK. |
| 3 | MUNICIPIO | 96 | MAESTRO | `nucleo_agrario.id_municipio` | Resolver por catálogo. |
| 4 | RESIDENCIA | 96 | PROYECTO_NUCLEO | `proyecto_nucleo.residencia` | Dato del seguimiento del núcleo dentro del proyecto. |
| 5 | CONSECUTIVO | 96 | PROYECTO_NUCLEO | `proyecto_nucleo.consecutivo` | Consecutivo operativo de seguimiento. |
| 6 | NÚCLEO AGRARIO | 96 | MAESTRO | `nucleo_agrario.nombre_nucleo` | Resolver/crear maestro y relación proyecto_nucleo. |
| 7 | E/C | 94 | MAESTRO | `nucleo_agrario.tipo_nucleo` | Normalizar E→ejido, C→comunidad. |
| 8 | NOMBRE DE LA PERSONA ORGANIZADORA AGRARIA RESPONSABLE | 68 | PROYECTO_NUCLEO | `proyecto_nucleo.responsable_nombre` | Responsable operativo por proyecto. |
| 9 | DATOS DE CONTACTO (TELÉFONO) | 65 | PROYECTO_NUCLEO | `proyecto_nucleo.responsable_telefono` | Contacto operativo. |
| 10 | DESTINO DE LA SUPERFICIE | 68 | AFECTACIÓN COLECTIVA | `afectacion.destino_superficie` | Destino/tipo del derecho colectivo. |
| 11 | NO. DE PARCELA/SOLAR | 19 | AFECTACIÓN COLECTIVA | `afectacion.no_parcela_solar NULL` | Referencia opcional; colectivo no exige parcela. |
| 12 | FECHA DE PADRÓN | 81 | PADRÓN | `padron_historial.fecha_padron` | Dato maestro/histórico del núcleo. |
| 13 | PADRÓN: NÚMERO DE EJIDATARIOS/ COMUNEROS | 57 | PADRÓN | `padron_historial.numero_ejidatarios_comuneros` | Dato maestro/histórico del núcleo. |
| 14 | ORV VIGENTES (SI/NO) | 95 | ORV | `orv / estado derivado de vigencia` | Preferir fechas y derivar vigencia; conservar valor fuente para importación/auditoría. |
| 15 | FECHA DE VENCIMIENTO DE ORV | 95 | ORV | `orv.fin_vigencia` | Fecha de fin de vigencia. |
| 16 | ACTA DE ELECCIÓN DE ORV INSCRITA EN EL RAN (SI/NO) | 85 | ORV | `orv.acta_eleccion_inscrita_ran` | Hecho registral del ORV. |
| 17 | CLAVE DEL TRAMO | 0 | REFERENCIA | `proyecto_nucleo.clave_tramo_referencia NULL` | Referencia histórica; no requiere entidad Tramo. |
| 18 | NÚMERO DE TRAMO | 0 | REFERENCIA | `proyecto_nucleo.numero_tramo_referencia NULL` | Referencia histórica; no requiere entidad Tramo. |
| 19 | REUNIÓN PROGRAMADA (FECHA) | 86 | ACTIVIDAD | `actividad_campo[sensibilizacion].fecha_programada` | Actividad inicial de proyecto_nucleo. |
| 20 | PROGRAMADA POR NA | 75 | DERIVADO | `DERIVAR por COUNT DISTINCT / existencia` | No persistir; es auxiliar de conteo Excel. |
| 21 | REUNIÓN REALIZADA (FECHA) | 86 | ACTIVIDAD | `actividad_campo[sensibilizacion].fecha_realizada` | Actividad inicial de proyecto_nucleo. |
| 22 | REALIZADA POR NA | 65 | DERIVADO | `DERIVAR por COUNT DISTINCT / existencia` | No persistir; es auxiliar de conteo Excel. |
| 23 | TRIMESTRE | 65 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 24 | PROGRAMADO (FECHA) | 86 | ACTIVIDAD | `actividad_campo[caminamiento].fecha_programada` | Actividad inicial de proyecto_nucleo. |
| 25 | PROGRAMADO POR NA | 65 | DERIVADO | `DERIVAR por COUNT DISTINCT / existencia` | No persistir; es auxiliar de conteo Excel. |
| 26 | REALIZADO (FECHA) | 86 | ACTIVIDAD | `actividad_campo[caminamiento].fecha_realizada` | Actividad inicial de proyecto_nucleo. |
| 27 | REALIZADO POR NA | 65 | DERIVADO | `DERIVAR por COUNT DISTINCT / existencia` | No persistir; es auxiliar de conteo Excel. |
| 28 | TRIMESTRE5 | 65 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 29 | ASAMBLEA PROGRAMADA 1/a (FECHA) | 77 | ASAMBLEA | `asamblea.fecha_prog_1a` | Conservar separado del RAN del convenio. |
| 30 | ASAMBLEA PROGRAMADA 2/a (FECHA) | 47 | ASAMBLEA | `asamblea.fecha_prog_2a` | Conservar separado del RAN del convenio. |
| 31 | PROGRAMADA POR NA2 | 51 | DERIVADO | `DERIVAR por COUNT DISTINCT / existencia` | No persistir; es auxiliar de conteo Excel. |
| 32 | ASAMBLEA REALIZADA (FECHA) | 75 | ASAMBLEA | `asamblea.fecha_realizada` | Conservar separado del RAN del convenio. |
| 33 | REALIZADA POR NA2 | 51 | DERIVADO | `DERIVAR por COUNT DISTINCT / existencia` | No persistir; es auxiliar de conteo Excel. |
| 34 | TRIMESTRE6 | 51 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 35 | FECHA PROGRAMADA DE INGRESO AL RAN | 0 | ASAMBLEA | `asamblea.campo_fuente_revision` | Conservar separado del RAN del convenio. |
| 36 | INGRESADO AL RAN (FECHA) | 60 | ASAMBLEA | `asamblea.ingreso_ran_fecha` | Conservar separado del RAN del convenio. |
| 37 | NÚMERO DE SOLICITUD DE INGRESO | 60 | ASAMBLEA | `asamblea.numero_solicitud_ran` | Conservar separado del RAN del convenio. |
| 38 | INGRESO POR NA | 44 | DERIVADO | `DERIVAR por COUNT DISTINCT / existencia` | No persistir; es auxiliar de conteo Excel. |
| 39 | TRIMESTRE7 | 44 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 40 | CALIFICACIÓN REGISTRAL3 | 5 | ASAMBLEA | `asamblea.calificacion_registral_ran` | Conservar separado del RAN del convenio. |
| 41 | ACTA INSCRITA EN EL RAN (FECHA) | 44 | ASAMBLEA | `asamblea.acta_inscripcion_fecha_ran` | Conservar separado del RAN del convenio. |
| 42 | IINSCRITO POR NA | 32 | DERIVADO | `DERIVAR por COUNT DISTINCT / existencia` | No persistir; es auxiliar de conteo Excel. |
| 43 | TRIMESTRE8 | 32 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 44 | ACTA COMPLEMENTARIA | 0 | ASAMBLEA | `asamblea.referencia_acta_complementaria` | Conservar separado del RAN del convenio. |
| 45 | ACUSE FIFONAFE (FECHA) | 0 | REVISIÓN | `documentacion_soporte / campo opcional` | Acuse FIFONAFE; no usado en muestra, confirmar necesidad. |
| 46 | AVALÚO MAESTRO (INDAABIN) $ | 11 | AVALÚO | `afectacion.avaluo_monto NULL / entidad simple si se confirma` | Dato real poco frecuente; requiere decisión funcional. |
| 47 | FECHA PROGRAMADA PARA FIRMA DE CONVENIO | 4 | PLANIFICACIÓN | `convenio.fecha_programada NULL` | Fecha programada; conservar si se usa. |
| 48 | CONVENIO FIRMADO (FECHA) | 58 | CONVENIO | `convenio[cop_original].fecha_firma` | Normalizar como fila de convenio, no columnas paralelas. |
| 49 | CONVENIO MONTO 90% | 51 | CONVENIO | `convenio[cop_original].monto_90` | Normalizar como fila de convenio, no columnas paralelas. |
| 50 | CONVENIO MONTO 100% | 55 | CONVENIO | `convenio[cop_original].monto_100` | Normalizar como fila de convenio, no columnas paralelas. |
| 51 | MONTO BDT | 0 | CONVENIO | `convenio[cop_original].monto_bdt` | Normalizar como fila de convenio, no columnas paralelas. |
| 52 | TRIMESTRE2 | 58 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 53 | FECHA PROGRAMADA DE INGRESO AL RAN. | 0 | PLANIFICACIÓN | `convenio.fecha_programada NULL` | Fecha programada; conservar si se usa. |
| 54 | INGRESADO AL RAN (FECHA). | 54 | CONVENIO | `convenio[cop_original].ingreso_ran_fecha` | Normalizar como fila de convenio, no columnas paralelas. |
| 55 | NÚMERO DE SOLICITUD DE INGRESO. | 54 | CONVENIO | `convenio[cop_original].numero_solicitud_ingreso` | Normalizar como fila de convenio, no columnas paralelas. |
| 56 | TRIMESTRE3 | 54 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 57 | CALIFICACIÓN REGISTRAL2 | 2 | CONVENIO | `convenio[cop_original].calificacion_registral` | Normalizar como fila de convenio, no columnas paralelas. |
| 58 | CONVENIO INSCRITO EN EL RAN (FECHA) | 41 | CONVENIO | `convenio[cop_original].convenio_inscrito_fecha_ran` | Normalizar como fila de convenio, no columnas paralelas. |
| 59 | TRIMESTRE4 | 41 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 60 | SUPERFICIE TOTAL PRELIMINAR (HA) | 11 | CONVENIO | `convenio[cop_original].superficie_ha` | Normalizar como fila de convenio, no columnas paralelas. |
| 61 | SUPERFICIE TOTAL REAL AFECTADA (HA)2 | 55 | CONVENIO | `convenio[cop_original].superficie_ha` | Normalizar como fila de convenio, no columnas paralelas. |
| 62 | ASAMBLEA PROGRAMADA 1/a (FECHA)2 | 1 | ASAMBLEA | `asamblea.fecha_prog_1a` | Conservar separado del RAN del convenio. |
| 63 | ASAMBLEA PROGRAMADA 2/a (FECHA)3 | 0 | ASAMBLEA | `asamblea.fecha_prog_2a` | Conservar separado del RAN del convenio. |
| 64 | ASAMBLEA REALIZADA (FECHA)2 | 0 | ASAMBLEA | `asamblea.fecha_realizada` | Conservar separado del RAN del convenio. |
| 65 | INGRESADO AL RAN (FECHA)3 | 0 | ASAMBLEA | `asamblea.ingreso_ran_fecha` | Conservar separado del RAN del convenio. |
| 66 | NÚMERO DE SOLICITUD DE INGRESO4 | 0 | ASAMBLEA | `asamblea.numero_solicitud_ran` | Conservar separado del RAN del convenio. |
| 67 | ACTA INSCRITA EN EL RAN (FECHA)2 | 0 | ASAMBLEA | `asamblea.acta_inscripcion_fecha_ran` | Conservar separado del RAN del convenio. |
| 68 | CONVENIO MODIFICATORIO FIRMADO (FECHA) | 0 | CONVENIO | `convenio[modificatorio].fecha_firma` | Normalizar como fila de convenio, no columnas paralelas. |
| 69 | CONVENIO MONTO 90%3 | 0 | CONVENIO | `convenio[modificatorio].monto_90` | Normalizar como fila de convenio, no columnas paralelas. |
| 70 | CONVENIO MONTO 100% 2 | 0 | CONVENIO | `convenio[modificatorio].monto_100` | Normalizar como fila de convenio, no columnas paralelas. |
| 71 | MONTO BDT2 | 0 | CONVENIO | `convenio[modificatorio].monto_bdt` | Normalizar como fila de convenio, no columnas paralelas. |
| 72 | TRIMESTRE22 | 0 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 73 | INGRESADO AL RAN (FECHA).3 | 0 | CONVENIO | `convenio[modificatorio].ingreso_ran_fecha` | Normalizar como fila de convenio, no columnas paralelas. |
| 74 | NÚMERO DE SOLICITUD DE INGRESO.4 | 0 | CONVENIO | `convenio[modificatorio].numero_solicitud_ingreso` | Normalizar como fila de convenio, no columnas paralelas. |
| 75 | CONVENIO INSCRITO EN EL RAN (FECHA)2 | 0 | CONVENIO | `convenio[modificatorio].convenio_inscrito_fecha_ran` | Normalizar como fila de convenio, no columnas paralelas. |
| 76 | SUPERFICIE TOTAL REAL AFECTADA (HA)22 | 0 | CONVENIO | `convenio[modificatorio].superficie_ha` | Normalizar como fila de convenio, no columnas paralelas. |
| 77 | REUNIÓN DE SENSIBILIZACIÓN PROGRAMADA (FECHA)2 | 1 | ACTIVIDAD | `actividad_campo[sensibilizacion,superficie_adicional].fecha_programada` | Actuación asociada a superficie adicional. |
| 78 | REUNIÓN DE SENSIBILIZACIÓN REALIZADA (FECHA) | 0 | ACTIVIDAD | `actividad_campo[sensibilizacion,superficie_adicional].fecha_realizada` | Actuación asociada a superficie adicional. |
| 79 | CAMINAMIENTO PROGRAMADO (FECHA)2 | 1 | ACTIVIDAD | `actividad_campo[caminamiento,superficie_adicional].fecha_programada` | Actuación asociada a superficie adicional. |
| 80 | PROGRAMADO POR NA3 | 1 | DERIVADO | `DERIVAR por COUNT DISTINCT / existencia` | No persistir; es auxiliar de conteo Excel. |
| 81 | CAMINAMIENTO REALIZADO (FECHA)4 | 1 | ACTIVIDAD | `actividad_campo[caminamiento,superficie_adicional].fecha_realizada` | Actuación asociada a superficie adicional. |
| 82 | REALIZADO POR NA5 | 1 | DERIVADO | `DERIVAR por COUNT DISTINCT / existencia` | No persistir; es auxiliar de conteo Excel. |
| 83 | TRIMESTRE56 | 1 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 84 | ASAMBLEA PROGRAMADA 1/a (FECHA)22 | 1 | ASAMBLEA | `asamblea.fecha_prog_1a` | Conservar separado del RAN del convenio. |
| 85 | ASAMBLEA PROGRAMADA 2/a (FECHA)33 | 0 | ASAMBLEA | `asamblea.fecha_prog_2a` | Conservar separado del RAN del convenio. |
| 86 | TRIMESTRE10 | 1 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 87 | ASAMBLEA REALIZADA (FECHA)24 | 1 | ASAMBLEA | `asamblea.fecha_realizada` | Conservar separado del RAN del convenio. |
| 88 | TRIMESTRE102 | 1 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 89 | INGRESADO AL RAN (FECHA)35 | 1 | ASAMBLEA | `asamblea.ingreso_ran_fecha` | Conservar separado del RAN del convenio. |
| 90 | NÚMERO DE SOLICITUD DE INGRESO46 | 1 | ASAMBLEA | `asamblea.numero_solicitud_ran` | Conservar separado del RAN del convenio. |
| 91 | TRIMESTRE1022 | 1 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 92 | ACTA INSCRITA EN EL RAN (FECHA)27 | 0 | ASAMBLEA | `asamblea.acta_inscripcion_fecha_ran` | Conservar separado del RAN del convenio. |
| 93 | CONVENIO SUP. ADICIONAL FIRMADO (FECHA)2 | 5 | CONVENIO | `convenio[superficie_adicional].fecha_firma` | Normalizar como fila de convenio, no columnas paralelas. |
| 94 | CONVENIO MONTO 90%2 | 4 | CONVENIO | `convenio[superficie_adicional].monto_90` | Normalizar como fila de convenio, no columnas paralelas. |
| 95 | CONVENIO MONTO 100% 3 | 5 | CONVENIO | `convenio[superficie_adicional].monto_100` | Normalizar como fila de convenio, no columnas paralelas. |
| 96 | MONTO BDT4 | 0 | CONVENIO | `convenio[superficie_adicional].monto_bdt` | Normalizar como fila de convenio, no columnas paralelas. |
| 97 | TRIMESTRE103 | 5 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 98 | INGRESADO AL RAN (FECHA).33 | 1 | CONVENIO | `convenio[superficie_adicional].ingreso_ran_fecha` | Normalizar como fila de convenio, no columnas paralelas. |
| 99 | NÚMERO DE SOLICITUD DE INGRESO.44 | 1 | CONVENIO | `convenio[superficie_adicional].numero_solicitud_ingreso` | Normalizar como fila de convenio, no columnas paralelas. |
| 100 | CONVENIO INSCRITO EN EL RAN (FECHA)25 | 0 | CONVENIO | `convenio[superficie_adicional].convenio_inscrito_fecha_ran` | Normalizar como fila de convenio, no columnas paralelas. |
| 101 | SUPERFICIE ADICIONAL (HA)22 | 5 | CONVENIO | `convenio[superficie_adicional].superficie_ha` | Normalizar como fila de convenio, no columnas paralelas. |
| 102 | REUNIÓN DE SENSIBILIZACIÓN PROGRAMADA (FECHA)2 | 0 | ACTIVIDAD | `actividad_campo[sensibilizacion,obras_complementarias].fecha_programada` | Actuación asociada a obras complementarias. |
| 103 | REUNIÓN DE SENSIBILIZACIÓN REALIZADA (FECHA) | 0 | ACTIVIDAD | `actividad_campo[sensibilizacion,obras_complementarias].fecha_realizada` | Actuación asociada a obras complementarias. |
| 104 | CAMINAMIENTO PROGRAMADO (FECHA). | 1 | ACTIVIDAD | `actividad_campo[caminamiento,obras_complementarias].fecha_programada` | Actuación asociada a obras complementarias. |
| 105 | CAMINAMIENTO REALIZADO (FECHA). | 1 | ACTIVIDAD | `actividad_campo[caminamiento,obras_complementarias].fecha_realizada` | Actuación asociada a obras complementarias. |
| 106 | ASAMBLEA 1A CONVOCATORIA (FECHA). | 1 | ASAMBLEA | `asamblea.fecha_prog_1a` | Conservar separado del RAN del convenio. |
| 107 | ASAMBLEA 2A CONVOCATORIA (FECHA). | 1 | ASAMBLEA | `asamblea.fecha_prog_2a` | Conservar separado del RAN del convenio. |
| 108 | ASAMBLEA REALIZADA (FECHA). | 1 | ASAMBLEA | `asamblea.fecha_realizada` | Conservar separado del RAN del convenio. |
| 109 | TRIMESTRE. | 1 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 110 | INGRESADO AL RAN (FECHA).2 | 0 | ASAMBLEA | `asamblea.ingreso_ran_fecha` | Conservar separado del RAN del convenio. |
| 111 | NÚMERO DE SOLICITUD DE INGRESO.2 | 0 | ASAMBLEA | `asamblea.numero_solicitud_ran` | Conservar separado del RAN del convenio. |
| 112 | TRIMESTRE.2 | 0 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 113 | CALIFICACIÓN REGISTRAL.. | 0 | ASAMBLEA | `asamblea.calificacion_registral_ran` | Conservar separado del RAN del convenio. |
| 114 | ACTA INSCRITA EN EL RAN (FECHA). | 0 | ASAMBLEA | `asamblea.acta_inscripcion_fecha_ran` | Conservar separado del RAN del convenio. |
| 115 | TRIMESTRE9 | 0 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 116 | CONVENIO FIRMADO (FECHA). | 1 | CONVENIO | `convenio[obras_complementarias].fecha_firma` | Normalizar como fila de convenio, no columnas paralelas. |
| 117 | CONVENIO MONTO 90%. | 1 | CONVENIO | `convenio[obras_complementarias].monto_90` | Normalizar como fila de convenio, no columnas paralelas. |
| 118 | CONVENIO MONTO 100% . | 1 | CONVENIO | `convenio[obras_complementarias].monto_100` | Normalizar como fila de convenio, no columnas paralelas. |
| 119 | TRIMESTRE11 | 1 | DERIVADO | `DERIVAR(fecha)` | No persistir; calcular desde la fecha correspondiente. |
| 120 | INGRESADO AL RAN (FECHA).. | 0 | CONVENIO | `convenio[obras_complementarias].ingreso_ran_fecha` | Normalizar como fila de convenio, no columnas paralelas. |
| 121 | NÚMERO DE SOLICITUD DE INGRESO.. | 0 | CONVENIO | `convenio[obras_complementarias].numero_solicitud_ingreso` | Normalizar como fila de convenio, no columnas paralelas. |
| 122 | CALIFICACIÓN REGISTRAL..2 | 0 | CONVENIO | `convenio[obras_complementarias].calificacion_registral` | Normalizar como fila de convenio, no columnas paralelas. |
| 123 | CONVENIO INSCRITO EN EL RAN (FECHA).. | 0 | CONVENIO | `convenio[obras_complementarias].convenio_inscrito_fecha_ran` | Normalizar como fila de convenio, no columnas paralelas. |
| 124 | SUPERFICIE TOTAL REAL AFECTADA (HA) | 1 | CONVENIO | `convenio[obras_complementarias].superficie_ha` | Normalizar como fila de convenio, no columnas paralelas. |
| 125 | ASAMBLEA 1A CONVOCATORIA (FECHA)2 | 8 | ASAMBLEA | `asamblea.fecha_prog_1a` | Conservar separado del RAN del convenio. |
| 126 | ASAMBLEA 2A CONVOCATORIA (FECHA)3 | 3 | ASAMBLEA | `asamblea.fecha_prog_2a` | Conservar separado del RAN del convenio. |
| 127 | ASAMBLEA REALIZADA (FECHA)24 | 6 | ASAMBLEA | `asamblea.fecha_realizada` | Conservar separado del RAN del convenio. |
| 128 | INGRESADO AL RAN (FECHA)25 | 3 | ASAMBLEA | `asamblea.ingreso_ran_fecha` | Conservar separado del RAN del convenio. |
| 129 | NÚMERO DE SOLICITUD DE INGRESO26 | 3 | ASAMBLEA | `asamblea.numero_solicitud_ran` | Conservar separado del RAN del convenio. |
| 130 | CALIFICACIÓN REGISTRAL.7 | 0 | ASAMBLEA | `asamblea.calificacion_registral_ran` | Conservar separado del RAN del convenio. |
| 131 | ACTA INSCRITA EN EL RAN (FECHA)38 | 2 | ASAMBLEA | `asamblea.acta_inscripcion_fecha_ran` | Conservar separado del RAN del convenio. |
| 132 | ESTATUS (COMPLETO, PENDIENTE, PROGRAMADO) | 4 | INDEMNIZACIÓN | `indemnizacion.estatus / tramite_fifonafe.estatus` | Conservar estatus administrativo; pago es hecho separado. |
| 133 | ENTREGA DE EXPEDIENTE SICT - PROCURADURÍA AGRARIA | 0 | REVISIÓN | `expediente_entrega_sict_pa NULL` | Campo sin datos en muestra; no diseñar entidad hasta confirmar uso. |
| 134 | EXPROPIACIÓN DIRECTA | 1 | CONDICIÓN | `afectacion/proyecto_nucleo.expropiacion_directa` | Definir alcance real por núcleo/proyecto/afectación; no inferir terminalidad global. |
| 135 | EL PROYECTO FERROVIARIO NO AFECTA TIERRAS DE USO COMÚN | 3 | CONDICIÓN | `afectacion/proyecto_nucleo.no_afecta_uso_comun` | Definir alcance real por núcleo/proyecto/afectación; no inferir terminalidad global. |
| 136 | COMUNIDAD INDÍGENA | 9 | CONDICIÓN | `afectacion/proyecto_nucleo.comunidad_indigena` | Definir alcance real por núcleo/proyecto/afectación; no inferir terminalidad global. |
| 137 | NO. DE OFICIO FIFONAFE A DGAOPR/REPRESENTACIÓN Y FECHA | 26 | FIFONAFE | `tramite_fifonafe.oficio_fifonafe_a_dgaopr + fecha` | Separar número y fecha al capturar/importar. |
| 138 | NO. DE OFICIO DGAOPR A REPRESENTACIÓN Y FECHA | 20 | FIFONAFE | `tramite_fifonafe.oficio_dgaopr_a_repr + fecha` | Separar número y fecha al capturar/importar. |
| 139 | RESPUESTA REPRESENTACIÓN A DGAOPR NO. DE OFICIO Y FECHA | 26 | FIFONAFE | `tramite_fifonafe.respuesta_repr_a_dgaopr + fecha` | Separar número y fecha al capturar/importar. |
| 140 | RESPUESTA DGAOPR/REPRESENTACIÓN A FIFONAFE NO. DE OFICIO Y FECHA | 24 | FIFONAFE | `tramite_fifonafe.respuesta_dgaopr_a_fifonafe + fecha` | Separar número y fecha al capturar/importar. |
| 141 | OBSERVACIONES / ACUERDOS | 1 | OBSERVACIÓN | `observaciones / minuta-acuerdo si procede` | Texto fuente; estructurar acuerdos sólo cuando aporte valor. |
| 142 | VALIDACIÓN PA/SICT | 0 | REVISIÓN | `validacion_pa_sict NULL` | Sin datos en muestra; confirmar antes de modelar. |
| 143 | OFICIO RAN PARCELAS CON AFECTACIÓN | 39 | RAN | `referencia_oficio_ran_parcelas NULL` | Referencia documental; valorar tabla/documento. |
| 144 | OBSERVACIONES | 60 | OBSERVACIÓN | `observaciones / minuta-acuerdo si procede` | Texto fuente; estructurar acuerdos sólo cuando aporte valor. |
| 145 | SOPORTE DOCUMENTAL | 86 | DOCUMENTO | `documentacion_soporte/documento_version` | Conservar evidencia y faltantes. |

## 4. Hallazgos de normalización

- Las columnas `TRIMESTRE*` son derivables desde fechas y no deben persistirse.
- Las columnas `PROGRAMADA POR NA`, `REALIZADA POR NA`, `INGRESO POR NA`, `INSCRITO POR NA` son auxiliares de conteo del Excel; el modelo debe derivar esos KPI por núcleo.
- Los bloques COP/modificatorio/superficie adicional/obras complementarias/ampliación/remanente se normalizan en múltiples filas de `convenio`.
- Los cuatro oficios de FIFONAFE se conservan; en captura conviene separar número y fecha.
- Los campos `CLAVE DEL TRAMO`/`NÚMERO DE TRAMO` se preservan sólo como referencia opcional durante migración.
- Los campos con cero datos en la muestra no justifican por sí mismos nuevas entidades.
- `SOPORTE DOCUMENTAL` y observaciones son información real y deben migrarse aun cuando el modelo documental se simplifique.

## 5. Cobertura del modelo objetivo

El objetivo de implementación es que cada fila de esta matriz termine en uno de tres estados:

1. **PERSISTIR**: tiene entidad/campo objetivo.
2. **DERIVAR**: se calcula a partir de hechos persistidos.
3. **REVISAR/NO IMPLEMENTAR AÚN**: requiere decisión funcional explícita, preservando el valor fuente durante la migración.

No se permite eliminar una columna con datos reales sin indicar su destino o una decisión aprobada.
