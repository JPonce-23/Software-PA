# Matriz Excel colectivo -> modelo operativo 036

Fuente prioritaria auditada: `Copia SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS MQ_COLECTIVOS MEET 27082026.xlsx`, hoja `INFORME M-Q`, rango físico A:CL (90 columnas), 146 filas operativas (filas 6–151), SHA-256 `38092fafed5e9fd3dac58178ad5714754537bb69b4be03ee5f26c3ece57d9fc1`. El archivo permanece fuera de Git. Esta matriz no reproduce nombres ni teléfonos.

Abreviaturas: PN = `proyecto_nucleo`; TF = `trazabilidad_fuente`; ITC = `importacion_tabular_celda`; cat. = `catalogo_operativo`. Toda celda importada conserva archivo/hash/hoja/fila/columna, valor original/normalizado, tratamiento y mensajes mediante `importacion_tabular` + ITC + TF. Estado `DERIVADO` significa que no se persiste el indicador Excel.

| FUENTE_EXCEL | CONCEPTO_FUNCIONAL | GRANULARIDAD | TABLA | COLUMNA/FK | CARDINALIDAD | CATÁLOGO | TRANSFORMACIÓN | VALIDACIÓN | TRAZABILIDAD | ESTADO |
|---|---|---|---|---|---|---|---|---|---|---|
| A NUM. | ordinal de fuente | fila Excel | ITC | `fila`, `valor_original` | N celdas/importación | no | referencia, no identidad | entero si aplica | ITC/TF | REFERENCIA |
| B ENTIDAD | entidad federativa | territorio | `entidad_federativa` | `id_entidad` vía municipio | 1:N municipios | INEGI existente | alias/nombre -> clave | municipio pertenece a entidad | ITC/TF | IMPLEMENTADO |
| C MUNICIPIO | municipio | territorio | `municipio` | `id_municipio` | N:1 entidad | INEGI existente | trim/alias territorial | entidad-municipio válidos | ITC/TF | IMPLEMENTADO |
| D RESIDENCIA | unidad PA | PN/histórico | PN | `id_residencia` | N:1 cat. | `residencia_pa` | alias -> código | tipo de catálogo y vigencia | ITC/TF | IMPLEMENTADO |
| E CONSECUTIVO | referencia administrativa | PN | `proyecto_nucleo_referencia` | `tipo_referencia=consecutivo`, `valor` | 1:N PN | tipo controlado existente | texto preservado | una principal activa/tipo | ITC/TF | IMPLEMENTADO |
| F NÚCLEO AGRARIO | núcleo RAN | núcleo | `nucleo_agrario` | `id_nucleo` | N:1 municipio | catálogo RAN existente | resolución exacta/alias aprobado | identidad natural activa | ITC/TF | IMPLEMENTADO |
| G E/C | tipo de tenencia | núcleo | `nucleo_agrario` | `id_tipo_tenencia` | N:1 cat. | `tipo_tenencia` | E->ejido, C->comunidad; blanco revisable | catálogo activo al capturar | ITC/TF | IMPLEMENTADO |
| H RESPONSABLE NOMBRE | responsable operativo | periodo PN | `proyecto_nucleo_responsable` | `nombre` | 1:N PN | no | trim; sin fixture | obligatorio en registro | ITC/TF restringida | IMPLEMENTADO |
| I CONTACTO | contacto responsable | periodo PN | `proyecto_nucleo_responsable` | `contacto` | 1:N PN | no | texto; no versionar | longitud; acceso autorizado | ITC/TF restringida | IMPLEMENTADO |
| J DESTINO SUPERFICIE | destino canónico del bien | bien | `bien_afectado` | `id_destino_superficie` | N:1 cat. | `destino_superficie` | acentos/aliases; textos con nombre de núcleo quedan detalle | tipo catálogo; opción histórica visible | ITC/TF | IMPLEMENTADO |
| K NO. PARCELA/SOLAR | referencia agraria | bien | `bien_afectado` | `referencia_alfanumerica`, `id_parcela?` | 1:N afectación | no | trim, conserva formato | varchar; parcela opcional mismo núcleo | ITC/TF | IMPLEMENTADO |
| L TIPO_GESTION | modalidad operativa | bien | `bien_afectado` | `id_tipo_gestion` | N:1 cat. | `tipo_gestion` | TUC/PARCELA -> código | independiente de ámbito | ITC/TF | IMPLEMENTADO |
| M TIPO COP | variante visible | bien/planeación | `bien_afectado` | `id_tipo_cop_operativo` | N:1 cat. | `tipo_cop_operativo` | mapea a tipo jurídico+secuencia al crear convenio | no crea convenio por fila | ITC/TF | IMPLEMENTADO |
| N FECHA PADRÓN | corte de padrón | núcleo/corte | `padron_historial` | `fecha_padron` | 1:N núcleo | no | una fecha por hecho; múltiples crean cortes; SD revisable | date, misma fuente/núcleo | ITC/TF | IMPLEMENTADO |
| O NÚMERO PADRÓN | población del corte | núcleo/corte | `padron_historial` | `numero_ejidatarios_comuneros` | 1:N núcleo | no | entero normalizado | >=0; fecha o número requerido | ITC/TF | IMPLEMENTADO |
| P ORV VIGENTE | estatus de fuente | ORV | `orv`/`vw_orv_estado` | `estatus_fuente`/derivado | 1:N núcleo | no | SI/NO se conserva; UI deriva por vigencia | contradicción advertida | ITC/TF | IMPLEMENTADO |
| Q VENCIMIENTO ORV | fin de vigencia | ORV | `orv` | `fin_vigencia` | 1:N núcleo | no | fecha | >= inicio | ITC/TF | IMPLEMENTADO |
| R ACTA ORV INSCRITA RAN | estado registral | ORV | `orv` | `id_estado_registral` | N:1 cat. | `estado_registral_orv` | SI->inscrita; NO->no_ingresada sólo con evidencia; PROCESO->en_proceso | no colapsa proceso a no | ITC/TF | IMPLEMENTADO |
| S COMUNIDAD INDÍGENA | atributo independiente | núcleo | `nucleo_agrario` | `comunidad_indigena` | 1:1 | no | SI/NO/NULL | sin default; no inferir de tenencia | ITC/TF | IMPLEMENTADO |
| T TOTAL COPS A FIRMAR | cantidad planeada | PN | PN | `total_cops_planeados` | 1:1 | no | entero; no COUNT filas | >=0 | ITC/TF | IMPLEMENTADO |
| U CLAVE TRAMO | referencia histórica | PN | `proyecto_nucleo_referencia` | `tipo_referencia=clave_tramo` | 1:N PN | no | texto | no crea TramoNucleo | ITC/TF | IMPLEMENTADO |
| V NÚMERO TRAMO | referencia histórica | PN | `proyecto_nucleo_referencia` | `tipo_referencia=numero_tramo` | 1:N PN | no | texto | no crea expediente tramo | ITC/TF | IMPLEMENTADO |
| W REUNIÓN PROGRAMADA | sensibilización programada | evento PN | `actividad_campo` | `tipo=sensibilizacion`, `fecha_programada` | 1:N PN | tipo existente | fecha | al menos una fecha | ITC/TF | IMPLEMENTADO |
| X PROGRAMADA POR NA1 | indicador de W | reporte | vista/query | `W IS NOT NULL` | derivada | no | X no se persiste | coherencia con W | ITC/TF como derivar | DERIVADO |
| Y TRIMESTRE1 | trimestre W | reporte | vista/query | `quarter(fecha_programada)` | derivada | no | cálculo de fecha | 1..4 | ITC/TF como derivar | DERIVADO |
| Z REUNIÓN REALIZADA | sensibilización realizada | evento PN | `actividad_campo` | `fecha_realizada` | 1:N PN | tipo existente | fecha | realizada puede existir sin programada | ITC/TF | IMPLEMENTADO |
| AA REALIZADA POR NA1 | indicador de Z | reporte | vista/query | `Z IS NOT NULL` | derivada | no | no persistir X | coherencia con Z | ITC/TF como derivar | DERIVADO |
| AB TRIMESTRE2 | trimestre Z | reporte | vista/query | `quarter(fecha_realizada)` | derivada | no | cálculo de fecha | 1..4 | ITC/TF como derivar | DERIVADO |
| AC PROGRAMADO | caminamiento programado | evento PN | `actividad_campo` | `tipo=caminamiento`, `fecha_programada` | 1:N PN | tipo existente | fecha | al menos una fecha | ITC/TF | IMPLEMENTADO |
| AD PROGRAMADA POR NA2 | indicador AC | reporte | vista/query | `AC IS NOT NULL` | derivada | no | no persistir | coherencia | ITC/TF como derivar | DERIVADO |
| AE TRIMESTRE3 | trimestre AC | reporte | vista/query | `quarter(fecha_programada)` | derivada | no | cálculo | 1..4 | ITC/TF como derivar | DERIVADO |
| AF REALIZADO | caminamiento realizado | evento PN | `actividad_campo` | `fecha_realizada` | 1:N PN | tipo existente | fecha | realizada sin programada válida | ITC/TF | IMPLEMENTADO |
| AG REALIZADA POR NA2 | indicador AF | reporte | vista/query | `AF IS NOT NULL` | derivada | no | no persistir | coherencia | ITC/TF como derivar | DERIVADO |
| AH TRIMESTRE4 | trimestre AF | reporte | vista/query | `quarter(fecha_realizada)` | derivada | no | cálculo | 1..4 | ITC/TF como derivar | DERIVADO |
| AI ASAMBLEA PROGRAMADA 1/a | primera convocatoria | convocatoria | `asamblea_convocatoria` | `ordinal=1`, `fecha_programada` | 1:N asamblea | resultado cat. | fecha; dedup clave funcional | ordinal único/asamblea | ITC/TF | IMPLEMENTADO |
| AJ ASAMBLEA PROGRAMADA 2/a | segunda convocatoria | convocatoria | `asamblea_convocatoria` | `ordinal=2`, `fecha_programada` | 1:N asamblea | resultado cat. | fecha; no límite de 2 | ordinal único/asamblea | ITC/TF | IMPLEMENTADO |
| AK PROGRAMADA POR NA3 | indicador AI/AJ | reporte | vista/query | existe convocatoria programada | derivada | no | no persistir | coherencia | ITC/TF como derivar | DERIVADO |
| AL TRIMESTRE5 | trimestre convocatoria | reporte | vista/query | quarter de fecha | derivada | no | cálculo | 1..4 | ITC/TF como derivar | DERIVADO |
| AM ASAMBLEA REALIZADA | celebración | asamblea/convocatoria | `asamblea_convocatoria` | `fecha_realizacion`, `id_resultado=celebrada` | 1:N asamblea | `resultado_convocatoria` | asociar al intento respaldado | no asumir ordinal sin evidencia | ITC/TF | IMPLEMENTADO |
| AN REALIZADA POR NA3 | indicador AM | reporte | vista/query | existe celebrada | derivada | no | no persistir | coherencia | ITC/TF como derivar | DERIVADO |
| AO TRIMESTRE6 | trimestre AM | reporte | vista/query | quarter de fecha | derivada | no | cálculo | 1..4 | ITC/TF como derivar | DERIVADO |
| AP FECHA PROGRAMADA INGRESO RAN | planeación RAN asamblea | trámite | `tramite_ran_evento` | tipo ingreso, observación/fecha planeada de compatibilidad | 1:N trámite | `tipo_evento_ran` | no sustituye ingreso real | objetivo asamblea | ITC/TF | IMPLEMENTADO |
| AQ INGRESADO RAN | ingreso real asamblea | evento RAN | `tramite_ran_evento` | `id_tipo_evento=ingreso`, `fecha_evento` | 1:N trámite | `tipo_evento_ran` | evento separado | fecha requerida | ITC/TF | IMPLEMENTADO |
| AR NÚMERO SOLICITUD | solicitud asamblea | evento RAN | `tramite_ran_evento` | `numero_solicitud` | 1:N trámite | no | texto | evento/objetivo tipado | ITC/TF | IMPLEMENTADO |
| AS INGRESO POR NA1 | indicador AQ | reporte | vista/query | existe evento ingreso | derivada | no | no persistir | coherencia | ITC/TF como derivar | DERIVADO |
| AT TRIMESTRE7 | trimestre AQ | reporte | vista/query | quarter de evento | derivada | no | cálculo | 1..4 | ITC/TF como derivar | DERIVADO |
| AU CALIFICACIÓN REGISTRAL | calificación asamblea | evento RAN | `tramite_ran_evento` | tipo calificación, `calificacion` | 1:N trámite | tipo evento cat. | evento sucesivo | no sobrescribe intento | ITC/TF | IMPLEMENTADO |
| AV ACTA INSCRITA RAN | inscripción asamblea | evento RAN | `tramite_ran_evento` | tipo inscripción, `fecha_evento` | 1:N trámite | tipo evento cat. | evento separado | secuencia preservada | ITC/TF | IMPLEMENTADO |
| AW INSCRITO POR NA1 | indicador AV | reporte | vista/query | existe inscripción | derivada | no | no persistir | coherencia | ITC/TF como derivar | DERIVADO |
| AX TRIMESTRE8 | trimestre AV | reporte | vista/query | quarter de evento | derivada | no | cálculo | 1..4 | ITC/TF como derivar | DERIVADO |
| AY FECHA PROGRAMADA FIRMA | planeación convenio | convenio | `convenio` | `fecha_programada_firma` | 1:N PN | no | fecha; dedup por hechos | fecha válida | ITC/TF | IMPLEMENTADO |
| AZ CONVENIO FIRMADO | firma | convenio | `convenio` | `fecha_firma` | 1:N PN | tipo jurídico controlado | fecha; no una fila=convenio | coherencia de ámbito y vínculos | ITC/TF | IMPLEMENTADO |
| BA MONTO 90% | monto convenio | convenio | `convenio` | `monto_90` | 1:1 convenio | no | decimal monetario | >=0 | ITC/TF | IMPLEMENTADO |
| BB MONTO 100% | monto convenio | convenio | `convenio` | `monto_100` | 1:1 convenio | no | decimal monetario | >=0 | ITC/TF | IMPLEMENTADO |
| BC MONTO BDT | monto BDT | convenio | `convenio` | `monto_bdt` | 1:1 convenio | no | decimal monetario | >=0 | ITC/TF | IMPLEMENTADO |
| BD TRIMESTRE9 | trimestre firma | reporte | vista/query | quarter(fecha_firma) | derivada | no | cálculo | 1..4 | ITC/TF como derivar | DERIVADO |
| BE FECHA PROGRAMADA RAN CONVENIO | planeación | trámite convenio | `tramite_ran_evento` | compatibilidad/observación planeada | 1:N trámite | tipo evento cat. | separado de ingreso real | objetivo convenio | ITC/TF | IMPLEMENTADO |
| BF INGRESADO RAN CONVENIO | ingreso | evento RAN | `tramite_ran_evento` | ingreso/fecha | 1:N trámite | `tipo_evento_ran` | evento | historial | ITC/TF | IMPLEMENTADO |
| BG NÚMERO SOLICITUD CONVENIO | solicitud | evento RAN | `tramite_ran_evento` | `numero_solicitud` | 1:N trámite | no | texto | asociado a evento | ITC/TF | IMPLEMENTADO |
| BH TRIMESTRE10 | trimestre BF | reporte | vista/query | quarter(evento) | derivada | no | cálculo | 1..4 | ITC/TF como derivar | DERIVADO |
| BI CALIFICACIÓN REGISTRAL CONVENIO | calificación | evento RAN | `tramite_ran_evento` | calificación/resultado | 1:N trámite | tipo evento cat. | evento sucesivo | no sobrescribe | ITC/TF | IMPLEMENTADO |
| BJ CONVENIO INSCRITO RAN | inscripción | evento RAN | `tramite_ran_evento` | inscripción/fecha | 1:N trámite | tipo evento cat. | evento | historial | ITC/TF | IMPLEMENTADO |
| BK TRIMESTRE11 | trimestre BJ | reporte | vista/query | quarter(evento) | derivada | no | cálculo | 1..4 | ITC/TF como derivar | DERIVADO |
| BL SUPERFICIE PRELIMINAR HA | superficie administrativa | bien/convenio | `bien_afectado` | `superficie_preliminar_ha` | 1:N afectación | no | formato agrario -> ha; original preservado | >=0; no geometría | ITC/TF | IMPLEMENTADO |
| BM SUPERFICIE REAL AFECTADA HA2 | superficie fuente | bien | `bien_afectado` | `superficie_afectada_ha`, original/formato | 1:N afectación | no | ha canónica | >=0 | ITC/TF | IMPLEMENTADO |
| BN SUPERFICIE REAL m2 | unidad derivada/fuente | reporte | vista/query | ha*10000 | derivada | no | comparar con fuente; no segunda verdad | tolerancia/advertencia | ITC/TF | DERIVADO |
| BO SUPERFICIE REAL ha | unidad canónica | bien | `bien_afectado` | `superficie_afectada_ha` | 1:N afectación | no | normalizar; conservar original | >=0 | ITC/TF | IMPLEMENTADO |
| BP SUPERFICIE TOTAL KM2 | unidad derivada | reporte | vista/query | ha/100 | derivada | no | cálculo | comparar con fuente | ITC/TF | DERIVADO |
| BQ ASAMBLEA 1A CONVOCATORIA2 | convocatoria retiro/fifonafe | convocatoria | `asamblea_convocatoria` | ordinal 1/fecha | 1:N asamblea | tipo/contexto cat. | contexto retiro_fondos cuando respaldado | dedup por hecho | ITC/TF | IMPLEMENTADO |
| BR ASAMBLEA 2A CONVOCATORIA3 | segunda convocatoria | convocatoria | `asamblea_convocatoria` | ordinal 2/fecha | 1:N asamblea | resultado cat. | no límite a 2 | ordinal único | ITC/TF | IMPLEMENTADO |
| BS ASAMBLEA REALIZADA24 | celebración retiro | convocatoria | `asamblea_convocatoria` | realización/celebrada | 1:N asamblea | resultado cat. | evento | contexto coherente | ITC/TF | IMPLEMENTADO |
| BT INGRESADO RAN25 | ingreso acta retiro | evento RAN | `tramite_ran_evento` | ingreso/fecha | 1:N trámite | tipo evento cat. | evento | objetivo asamblea | ITC/TF | IMPLEMENTADO |
| BU NÚMERO SOLICITUD26 | solicitud retiro | evento RAN | `tramite_ran_evento` | `numero_solicitud` | 1:N trámite | no | texto | evento tipado | ITC/TF | IMPLEMENTADO |
| BV CALIFICACIÓN REGISTRAL7 | calificación retiro | evento RAN | `tramite_ran_evento` | calificación | 1:N trámite | tipo evento cat. | evento | historial | ITC/TF | IMPLEMENTADO |
| BW ACTA INSCRITA RAN38 | inscripción retiro | evento RAN | `tramite_ran_evento` | inscripción/fecha | 1:N trámite | tipo evento cat. | evento | historial | ITC/TF | IMPLEMENTADO |
| BX ESTATUS | estatus FIFONAFE/expediente | trámite | `tramite_fifonafe` | `estatus` | 1:N PN | dominio existente | normalizar completo/pendiente/programado | reglas de completitud | ITC/TF | IMPLEMENTADO |
| BY ENTREGA EXPEDIENTE SICT-PA | hito indemnización | afectación | `indemnizacion` | `fecha_entrega_expediente_pa` | 0:1 activa afectación | no | fecha | mismo contexto por FK | ITC/TF | IMPLEMENTADO |
| BZ EXPROPIACIÓN DIRECTA | condición/ruta | afectación | `afectacion` | `condicion_especial`, detalle | 1:1 afectación | dominio existente | indicador -> expropiación directa | detalle coherente | ITC/TF | IMPLEMENTADO |
| CA NO AFECTA TUC | resultado de diagnóstico | PN/afectación | ITC/TF | tratamiento/referencia | N:1 PN | no | no crear afectación ficticia | revisión; no inferir ámbito | ITC/TF | DOCUMENTADO |
| CB COMUNIDAD INDÍGENA | reiteración/control | núcleo | `nucleo_agrario` | `comunidad_indigena` | 1:1 | no | reconciliar con S; vacío=NULL | contradicción genera advertencia | ITC/TF | IMPLEMENTADO |
| CC OFICIO FIFONAFE->DGAOPR | correspondencia | evento FIFONAFE | `tramite_fifonafe_evento` | origen/destino/número/fecha | 1:N trámite | `tipo_evento_fifonafe` | separar número y fecha | uno de número/fecha requerido | ITC/TF | IMPLEMENTADO |
| CD OFICIO DGAOPR->REPRESENTACIÓN | correspondencia | evento FIFONAFE | `tramite_fifonafe_evento` | origen/destino/número/fecha | 1:N trámite | tipo evento cat. | evento; reenvíos permitidos | ordinal único | ITC/TF | IMPLEMENTADO |
| CE RESPUESTA REPRESENTACIÓN->DGAOPR | correspondencia | evento FIFONAFE | `tramite_fifonafe_evento` | origen/destino/número/fecha | 1:N trámite | tipo evento cat. | evento repetible | historial | ITC/TF | IMPLEMENTADO |
| CF RESPUESTA DGAOPR->FIFONAFE | correspondencia | evento FIFONAFE | `tramite_fifonafe_evento` | origen/destino/número/fecha | 1:N trámite | tipo evento cat. | evento repetible | historial | ITC/TF | IMPLEMENTADO |
| CG OBSERVACIONES/ACUERDOS | contexto no estructurado | entidad aplicable | entidad/ITC | `observaciones`/mensajes | N:1 | no | sólo complemento, nunca hecho obligatorio | longitud/contexto | ITC/TF | IMPLEMENTADO |
| CH VALIDACIÓN PA/SICT | validación documental | checklist | `expediente_requisito` | `id_requisito`, `id_estado` | 1:N PN | requisito/estado | estado estructurado | objetivo del mismo PN | ITC/TF | IMPLEMENTADO |
| CI OFICIO RAN PARCELAS AFECTACIÓN | soporte registral | documento/evento | `documento`, `documento_vinculo` | vínculo a bien/afectación/evento | N:M lógico | tipo documento | metadatos; archivo fuera de Excel | objetivo existente | ITC/TF/documento | IMPLEMENTADO |
| CJ OBSERVACIONES | nota de seguimiento | entidad aplicable | entidad/ITC | `observaciones`/mensajes | N:1 | no | complemento | no sustituye evento | ITC/TF | IMPLEMENTADO |
| CK SOPORTE DOCUMENTAL | documento disponible | checklist/documento | `expediente_requisito` | estado disponible, `id_documento` | 1:N PN | `estado_requisito_documental` | estructurar lista; vincular documento | disponible requiere evidencia cuando aplique | ITC/TF | IMPLEMENTADO |
| CL SOPORTE DOCUMENTAL FALTANTE | faltante | checklist | `expediente_requisito` | `id_estado=faltante` | 1:N PN | estado/requisito | texto -> requisitos separados; desconocido revisable | no texto libre como única fuente | ITC/TF | IMPLEMENTADO |

## Reglas de deduplicación funcional

No se deduplica por similitud textual ni por número de fila. Primero se resuelve territorio/núcleo y el PN; después se aplican claves explícitas:

| Hecho | Clave funcional de importación |
|---|---|
| padrón | núcleo + fecha de emisión + número + fuente |
| ORV | núcleo + inicio/fin de vigencia + número/estado fuente |
| sensibilización/caminamiento | PN + tipo + contexto + fechas programada/realizada + responsable normalizado |
| asamblea | PN + tipo + contexto + padrón + fecha realizada; si faltan datos, queda en revisión |
| convocatoria | asamblea + ordinal + fechas + resultado |
| convenio | PN + ámbito + tipo jurídico + consecutivo + firma + asamblea autorizante + referencias registrales |
| trámite RAN | objetivo tipado + propósito; una nueva solicitud no reemplaza el trámite/evento previo |
| evento RAN | trámite + ordinal; el ordinal se asigna por secuencia documentada, no por fila |
| FIFONAFE | PN + ámbito + acuse/propósito; eventos por ordinal, origen/destino, número y fecha |
| bien | afectación + gestión + destino + referencia + superficie original; la afectación se decide por titularidad jurídica |

Una colisión exacta es idempotente; una discrepancia parcial se registra como advertencia y requiere resolución, no una combinación silenciosa.

## Fuentes oficiales consultadas

- Cámara de Diputados: [Ley Agraria vigente](https://www.diputados.gob.mx/LeyesBiblio/pdf/LAgra.pdf) y [Reglamento de la Ley Agraria en Materia de Ordenamiento de la Propiedad Rural](https://www.diputados.gob.mx/LeyesBiblio/regley/Reg_LAgra_MOPR.pdf).
- Registro Agrario Nacional: [PHINA](https://www.gob.mx/ran/es/articulos/que-es-el-padron-e-historial-de-nucleos-agrarios-phina?idiom=es), [Sistema de Información Geoespacial](https://www.gob.mx/ran/es/articulos/ya-conoces-el-sistema-de-informacion-geoespacial-sig?idiom=es) y [Datos Abiertos](https://datos.ran.gob.mx/conjuntoDatosPublico.php).
- Procuraduría Agraria: [directorio territorial](https://www.gob.mx/pa/documentos/128868), [servicios y acompañamiento agrario](https://pa.gob.mx/paweb/servicios/info_servicios.html) y [manual de órganos de representación](https://www.pa.gob.mx/pa/conoce/publicaciones/ley_glosario2014/glosario2014_25sep14_hq.pdf).
- FIFONAFE: [fondos comunes de uso individual](https://www.gob.mx/fifonafe/acciones-y-programas/fondos-comunes-uso-individual), [Lineamientos de Fondos Comunes](https://www.fifonafe.gob.mx/m_legal/LFC_2021.pdf) y [Manual de Procedimientos de Fondos Comunes](https://www.fifonafe.gob.mx/m_legal/MANUAL_DE_PROCEDIMIENTOS_DE_FONDOS_COMUNES.pdf).
