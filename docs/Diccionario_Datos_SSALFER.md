# Diccionario de datos vigente

## Entidades y campos V1

| Entidad | Campo/relación | Tipo conceptual / nullable | Significado y fuente Excel | API / reporting |
|---|---|---|---|---|
| ProyectoNucleo | id_proyecto, id_nucleo, afecta_tuc, total_cops_planeados | relaciones / sí | Unidad proyecto-núcleo; total COP y estado actual, no fecha histórica | proyectos/núcleos; snapshot actual |
| NucleoAgrario | municipio, comunidad_indigena | FK / sí | Núcleo, territorio y característica indígena | núcleos; `total_nucleos`, `comunidad_indigena` |
| Parcela | id_nucleo, tipo_parcela, no_parcela | FK/texto / no_parcela sí | Unidad individual; `no_parcela` es el único número funcional, también para NO PARCELA PPT coincidente | parcelas; `total_parcelas_afectadas` |
| ParcelaTitular | id_parcela, id_persona, tipo_derecho, vigencias | FKs/fechas / según campo | Titular canónico verificable; estados textuales ambiguos se trazan y no crean Persona | titulares, documentos |
| UnidadAgraria | id_parcela, tierra, titularidad, destino | FKs / parcela sí | Unidad agraria y destino físico de superficie | unidades agrarias; snapshot por destino |
| Afectacion | id_proyecto_nucleo, tipo_afectacion, COP, superficies | FKs/ha / según campo | Alcance colectivo o individual; ha administrativas independientes del desglose asociado | afectaciones; reporting/snapshot |
| ActividadCampo | tipo_actividad, fechas, id_tipo_cop_operativo | catálogo/fechas / COP sí | Sensibilización y caminamiento: unidad PN+COP, ámbito colectivo | actividades; avance temporal |
| Asamblea | tipo, contexto, id_tipo_cop_operativo | FKs / COP sí | Unidad canónica de Asamblea; retiro es flujo separado | asambleas; avance temporal |
| AsambleaConvocatoria | ordinal, fechas, resultado | 1:N / fechas sí | 1A, 2A y ulteriores; sólo celebrada realiza Asamblea | asambleas |
| TramiteRan | Asamblea/Convenio/ORV | FK exclusiva / sí | Expediente RAN; ingreso/reingreso es un hito | tramites-ran; avance |
| TramiteRanEvento | tipo, fecha_evento, solicitud, calificación | evento / fecha sí | Inscripción sólo por tipo `inscripcion`; calificación no equivale | tramites-ran; avance |
| Convenio | ambito, tipo_convenio, firma, superficie, monto | jurídico / fechas sí | Una unidad aun con N afectaciones; COP se deriva sin arbitrariedad | convenios; avance/dashboard |
| ConvenioAfectacion | id_convenio, id_afectacion, rol | N:M / no | Relación que clasifica el alcance sin multiplicar el convenio en reporting | convenios/afectaciones |
| AfectacionUnidadAgraria | unidad, superficie_afectada_ha | N:M / sí | Fuente canónica de superficie por destino en ha | afectaciones; snapshot |
| TramiteFifonafe | id_proyecto_nucleo, ambito, estatus, acuse, hay_conflictos | FK/estado / según campo | Trámite colectivo o individual; no conflictos es estado distinto de la cadena de oficios | fifonafe; avance sólo con fecha canónica |
| TramiteFifonafeEvento | tipo, numero_oficio, fecha_oficio | evento / sí | Colectivo completo: 4 códigos, número y fecha; MAX sólo de ellos | fifonafe; avance |
| Indemnizacion | id_afectacion, estatus, fecha_programada, fecha_resolucion | FK/fechas / fechas sí | `fecha_resolucion` es la fecha realizada; pagado sin ella no se periodiza | indemnizaciones; avance |
| Pago | id_indemnizacion, fecha_pago, monto, beneficiario_nombre | FK/fecha/monto / no | Pago real registrado en indemnización; `fecha_pago` y `monto` canónicos | pagos; avance temporal/dashboard (`indicador = 'pagos'`) |
| Documento | tipo, estado, fecha, folio, descripción | metadatos / según campo | Evidencia documental reutilizable mediante vínculos tipados y activos | documentos |
| ExpedienteRequisito | requisito, estado, objetivo, documento | FKs / documento sí | Cumplimiento documental por objetivo canónico | requisitos/documentos |
| TrazabilidadFuente | archivo, hoja, fila, columna, valor, tratamiento | referencia / según campo | Conserva procedencia y decisiones PERSISTIR, DERIVAR, REFERENCIA, DOCUMENTAR, REVISAR o NO IMPLEMENTAR | trazabilidad |
| SeguimientoEvento | fecha, documento, tipo/motivo | historial / fecha según tipo | Transiciones fechadas; documento activo del mismo PN | seguimiento; estado actual |
| DocumentoVinculo | documento, entidad objetivo | relación / no | Prueba de compatibilidad proyecto-núcleo | documentos; trigger 006 |

## Read-models

`vw_hito_seguimiento` representa hechos con fecha canónica; `vw_reporte_avance_periodo` agrega esos hechos por mes/trimestre derivado y `vw_dashboard_kpi` por año. `vw_reporte_snapshot_actual` no acepta dimensión temporal: expresa estado actual de núcleos, parcelas, superficies, no-afecta-TUC, comunidad indígena y COP planeados. Un corte histórico exacto no es reconstruible sin fuente fechada o snapshot explícito.

Fuente vigente: migraciones 001, 002, 003, 004, 005, 006, 007, 008, 009, 010, 011, 012, 013, 014 y 015. El schema actual es 015 y `GET /health` reporta `schema: 15`.

006 conserva las tablas de dominio y agrega read-models/validación. `Asamblea.id_tipo_cop_operativo` (FK catálogo) es la dimensión COP de asambleas y RAN de acta; retiro de fondos se identifica por tipo/contexto de Asamblea y usa indicadores propios. `vw_reporte_snapshot_actual` contiene estado actual sin fecha de negocio: `id_proyecto`, `id_entidad`, ámbito, indicador, COP/destino opcionales, cantidad, ha y monto. `seguimiento_evento.fecha_evento` es obligatoria para inicio, suspensión, reapertura, cierre y cambio de alcance; su documento debe estar activo y vinculado al mismo ProyectoNucleo.
013 incorpora la representación canónica de pagos en reporting a través de la cadena canónica `Pago → Indemnizacion → Afectacion → ProyectoNucleo → Proyecto`.
014 incorpora el read-model de detalle de convenios colectivos por destino. 015 excluye de los read-models vigentes todo proyecto con `activo IS NOT TRUE`, aunque su `ProyectoNucleo` permanezca activo.

- `seguimiento_evento`: entidad de historia funcional operativa con PK `id_seguimiento_evento`, FK `id_proyecto_nucleo`, objetivo opcional (`entidad_tipo`, `entidad_id`), `ambito` (general, colectivo, individual), `id_tipo_evento` (FK catalogo_operativo), `id_motivo` (FK catalogo_operativo nullable), `fecha_evento`, `detalle`, `id_documento`, `fuente`, auditoría y baja lógica.
- `catalogo_operativo.tipo_evento_seguimiento`: inicio, suspension, reapertura, cierre, cambio_alcance, reunion, negociacion, consulta_indigena, continuacion_asamblea, medicion_bdt, otro.
- `catalogo_operativo.motivo_seguimiento`: expropiacion_directa, no_afectacion, comunidad_indigena, dominio_pleno, juicio_agrario, conflicto_titularidad, rechazo, cambio_trazo, nueva_informacion, calificacion_negativa, falta_pago, otro.
- `catalogo_operativo.estado_requisito_documental`: adiciona parcial, pendiente_validacion a los preexistentes (pendiente, disponible, faltante, no_aplica, otro).
- `requisito_documental`: incorpora validacion_pa_sict (Validación PA/SICT), oficio_ran_parcelas_afectacion (Oficio RAN de parcelas con afectación) y acta_complementaria (Acta complementaria).
- `vw_seguimiento_estado_actual`: read-model determinista por proyecto-núcleo y objetivo (estado_actual, tipo_ultimo_evento, motivo_actual, fecha_ultimo_evento, detalle, ambito).
- `actividad_campo.id_tipo_cop_operativo`: FK nullable de ciclo reportable; conserva múltiples sensibilizaciones/caminamientos.
- `asamblea.id_tipo_cop_operativo`: FK nullable de ciclo reportable; Asamblea es entidad independiente.
- `catalogo_operativo.tipo_cop_operativo`: ORIGEN, ADICIONAL, 2A_ADICIONAL, COMPLEMENTARIAS, TRANSVERSALES.
- `indemnizacion.estatus`: pendiente, programado, en_proceso, completo, pagado, cancelado, otro.
- `expediente_requisito.entidad_tipo`: incluye orv, padron_historial, actividad_campo, asamblea, asamblea_convocatoria.
- `parcela.no_parcela`: único número funcional; no existe número PPT paralelo.
- `tramite_ran.fecha_programada_ingreso` y `tramite_ran_evento`: fechas, solicitudes, calificación e inscripción canónicas.
- `Asamblea` y `AsambleaConvocatoria`: una Asamblea es la unidad de conteo; convocatorias son 1:N y sólo la convocatoria con resultado `celebrada` aporta su fecha realizada. Una Asamblea de tipo/contexto `retiro_fondos` genera un único hito retiro, sin depender de texto libre ni de `seguimiento_evento`.
- `TramiteRan` y `TramiteRanEvento`: el trámite se vincula exactamente a Asamblea, Convenio u ORV; ingreso usa el primer evento `ingreso`/`reingreso`, y la inscripción sólo `fecha_evento` de evento `inscripcion`. Calificación, alta técnica y otros eventos no sustituyen inscripción.
- `Convenio`: conserva independientemente `ambito`, `tipo_convenio`, firmas, superficie y monto. `vw_convenio_tipo_cop_operativo` deriva COP desde afectaciones activas únicamente cuando es inequívoco; si hay ORIGEN y ADICIONAL, el COP queda `NULL` para revisión, nunca se elige uno.
- `AfectacionUnidadAgraria`: relación canónica para superficie por destino (`superficie_afectada_ha`); no se repite la superficie total de Afectacion por cada destino. Parcelas y núcleos son snapshots sin fecha histórica canónica.
- `TramiteFifonafe`/`TramiteFifonafeEvento`: colectivo se completa con los cuatro oficios fechados y fecha `MAX(fecha_oficio)`; individual no exige esa cadena. `hay_conflictos=false` es el hecho de no conflictos y no equivale por sí mismo a los cuatro oficios.
- `Indemnizacion`: `fecha_resolucion` es la única fecha realizada para reporting; estatus `pagado` sin ella permanece sin periodo y no exige Pago.
- `Pago`: representa pagos reales registrados mediante la cadena canónica `Pago → Indemnizacion → Afectacion → ProyectoNucleo → Proyecto`. Cada pago activo genera un hito propio en `vw_hito_seguimiento` (`clave_hito = 'pago:' || id_pago`, `indicador = 'pagos'`, `fecha_realizada = fecha_pago`, `monto = monto`, `programado = 0`, `superficie_ha = NULL`). Se agrega por mes/trimestre en `vw_reporte_avance_periodo` y anualmente en `vw_dashboard_kpi`. No se confunde con el estatus `pagado` de `Indemnizacion` (que sin `fecha_resolucion` no periodiza ni inventa pagos), ni con retiros FIFONAFE, ni con montos declarados en Convenios, ni con avalúos de indemnización. Previene duplicación por relaciones N:M (`ConvenioAfectacion`, `AfectacionUnidadAgraria`, `TramiteFifonafeAfectacion`) y se aísla estrictamente por proyecto y entidad.
- `vw_hito_seguimiento`: vista hito canónica que normaliza `clave_hito`, indicador, fechas de negocio, ámbito, COP, convenio, destino, cantidad, superficie y monto. Incluye snapshots sin fecha (núcleos, parcelas, superficies administrativas/destino) para consulta técnica, pero no los fecha con `creado_en`.
- `vw_reporte_avance_periodo`: desglose temporal de 15 columnas (`id_proyecto`, `id_entidad`, `ambito`, `tipo_cop_operativo`, `tipo_convenio`, `destino_superficie`, `anio`, `mes`, `trimestre`, `indicador`, `programado`, `realizado`, `cantidad`, `superficie_ha`, `monto`). Sólo proyecta fechas canónicas; trimestre deriva de la fecha.
- `vw_dashboard_kpi`: agregación anual directa sobre hitos deduplicados. `cantidad` cuenta `clave_hito` distinta; superficie/monto se proyectan sólo en realizado, por lo que programación y firma no los duplican.
- `vw_convenio_colectivo_destino`: read-model de detalle con granularidad de una fila por `id_convenio + destino_superficie` para convenios colectivos (`ambito = 'colectivo'`), derivado de la cadena canónica `Convenio -> ConvenioAfectacion -> Afectacion -> AfectacionUnidadAgraria -> UnidadAgraria -> CatalogoOperativo(destino_superficie)`. Separa la superficie física por destino (`sum(au.superficie_afectada_ha)`) de la superficie total declarada por el instrumento (`c.superficie_ha`); conserva `monto_declarado = c.monto_100` como atributo **NO ADITIVO** del convenio, sin prorrateo. La vista no calcula cantidades oficiales: al agregar sus filas, la cantidad de convenios debe deduplicarse por `id_convenio` y la de asambleas por `id_asamblea`; un agregado económico oficial debe contar cada `monto_declarado` una sola vez por `id_convenio`, nunca sumarlo directamente sobre filas multidestino. Reporta `NULL` cuando el destino o la superficie física no están determinados (NULL no es cero), consolida afectaciones múltiples del mismo destino dentro del convenio, respeta bajas lógicas y excluye proyectos con `activo IS NOT TRUE`.
- `docs/backend/MATRIZ_COBERTURA_EXCEL_V1.md`: trazabilidad Excel V1 con los tratamientos reales PERSISTIR, DERIVAR, REFERENCIA, DOCUMENTAR, REVISAR y NO IMPLEMENTAR.
