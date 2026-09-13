# Cambios de API respecto al Baseline V1

Estado vigente: schema 015, migraciones 001–015 y `GET /health` con `schema: 15`. La siguiente migración disponible es 016.

## 002_cierre_fuentes_excel

**Antes:** el reporte dependía de interpretaciones planas de hojas Excel y no clasificaba actividades/asambleas por ciclo operativo.

**Ahora:** `ActividadCampo` y `Asamblea` aceptan `id_tipo_cop_operativo`; el catálogo incluye `TRANSVERSALES` y el contexto de asamblea incluye `transversal`. Indemnización admite `en_proceso`, `pagado`, `cancelado`. Checklist acepta `orv`, `padron_historial`, `actividad_campo`, `asamblea`, `asamblea_convocatoria`.

**Impacto frontend:** aditivo. Las X no son campos API. RAN permanece normalizado como trámite/eventos; parcela conserva sólo `no_parcela`. FIFONAFE distingue flujo colectivo completo e individual.

## 003_reporting_fuentes_excel

**Antes:** dashboard agrupaba hitos con una fecha coalescida y no exponía inscripción RAN en forma compatible.

**Ahora:** conserva `GET /api/dashboard/kpi` y agrega `GET /api/reportes/avance-periodo`, con `id_proyecto`, `id_entidad`, `anio`, `mes`, `trimestre`, `indicador`. Recupera `inscripcion_ran_acta` e `inscripcion_ran_convenio`; ingreso y reingreso del mismo trámite cuentan una vez.

**Impacto frontend:** aditivo para el endpoint periódico; cambio de comportamiento correcto en periodos: programado y realizado se asignan a sus fechas propias. Mes/trimestre son derivados, no columnas persistidas.

## 004_seguimiento_funcional_excel

**Antes:** el sistema únicamente representaba el estado actual del seguimiento mediante columnas planas, perdiendo la historia funcional de transiciones críticas presentes en los Excel (expropiación directa seguida de reapertura, núcleos inicialmente sin afectación TUC que luego se afectan, parcelas no afectadas que luego reaparecen en nuevas presentaciones, consultas indígenas y continuación de asambleas permanentes).

**Ahora:**
- Se crea la entidad `seguimiento_evento` para registro histórico append-oriented de eventos funcionales.
- Endpoints incorporados:
  - `GET /api/proyecto-nucleo/{id_proyecto_nucleo}/seguimiento`: lista ordenada cronológicamente de eventos activos.
  - `POST /api/proyecto-nucleo/{id_proyecto_nucleo}/seguimiento`: registro de nuevo evento operativo tipado.
  - `GET /api/seguimiento/{id_seguimiento_evento}`: consulta detallada de un evento.
  - `PATCH /api/seguimiento/{id_seguimiento_evento}`: corrección de metadatos legítimos sin simular transiciones históricas.
  - `DELETE /api/seguimiento/{id_seguimiento_evento}`: baja lógica obligatoria con motivo y auditoría; eliminación física bloqueada en base de datos.
- Catálogos operativos incorporados: `tipo_evento_seguimiento` (11 opciones canónicas) y `motivo_seguimiento` (12 opciones canónicas).
- Catálogo documental ampliado con `parcial` y `pendiente_validacion`.
- Requisitos documentales agregados: `validacion_pa_sict`, `oficio_ran_parcelas_afectacion` y `acta_complementaria`.

**Impacto frontend:** aditivo. No modifica endpoints existentes ni fuerza estados ficticios de persona. Preserva la independencia entre la afectación física (`afecta_tuc`), las características territoriales (`comunidad_indigena`) y las suspensiones operativas temporales.

## 005_reporting_cierre_excel

**Antes:** el reporte periódico y dashboard presentaban riesgo de multiplicación o desalineación al no separar la deduplicación de hitos de la expansión temporal, carecían de desglose dimensional por ámbito, ciclo COP, subtipo de convenio y destino de superficie, y no integraban el historial funcional de seguimiento 004 ni los cierres específicos de FIFONAFE e indemnizaciones.

**Ahora:**
- Se implementa el read-model canónico en dos capas:
  1. `vw_hito_seguimiento`: consolida cada hito operativo (`clave_hito`) con sus fechas canónicas programada y realizada, su indicador, y sus dimensiones (`ambito`, `tipo_cop_operativo`, `tipo_convenio`, `destino_superficie`), deduplicando a nivel de hito antes de expandir periodos.
  2. `vw_reporte_avance_periodo`: desglose temporal de 15 columnas con filtros dimensionales completos (`ambito`, `tipo_cop_operativo`, `tipo_convenio`, `destino_superficie`), asignando `programado` y `realizado` a sus fechas respectivas sin inventar periodos ni duplicar cantidades.
  3. `vw_dashboard_kpi`: agregación de alto nivel por `id_proyecto, anio, indicador`, deduplicada anualmente.
- Se actualizan los schemas y routers del backend (`ReporteAvancePeriodoResponse`, `/api/reportes/avance-periodo`) manteniendo total compatibilidad hacia atrás con los clientes que consumían la versión previa.

**Impacto frontend:** aditivo y retrocompatible. Expone las 4 nuevas dimensiones en el reporte periódico y permite filtros avanzados en UI.

## 006_ajustes_reporting_post_auditoria

**Ahora:** Asamblea y RAN de acta conservan `tipo_cop_operativo`; retiro de fondos y su RAN se separan de Asamblea ordinaria. Se incorpora `GET /api/reportes/resumen-actual` para snapshots actuales sin fechas ficticias. FIFONAFE colectivo exige número y fecha en cada oficio canónico; no conflictos no genera periodo sin fecha propia.

En el corte histórico descrito por esta sección estaban vigentes 001–005 y la siguiente migración era 006.
El Modelo Excel V1 queda funcionalmente congelado en 005; 006+ sólo se justifica por requerimientos nuevos o defectos reales, no por campos ya presentes en las fuentes auditadas.

## 009_bitacora_append_only

**Ahora:** la bitácora queda disponible para consulta desde la aplicación, pero
el rol runtime no puede insertarla, actualizarla ni eliminarla directamente.

**Impacto frontend:** no hay endpoint nuevo ni cambio de body. La auditoría se
mantiene como evidencia generada por el backend; el frontend no debe intentar
escribir bitácora ni conectarse a PostgreSQL.

## 010_credenciales_auditoria

**Ahora:** se incorporan eventos de acceso para cambio de correo, cambio de
contraseña y restablecimiento administrativo. Los cambios exclusivos de hashes
de contraseña, token o CSRF no exponen secretos ni generan snapshots vacíos de
bitácora. Se habilitan los endpoints de sesión y administración de credenciales
descritos en el contrato frontend.

**Impacto frontend:** aditivo. El cliente usa cookies de sesión y CSRF; cambio
de correo, cambio/restablecimiento de contraseña y revocación devuelven el
conteo `sesiones_revocadas` cuando corresponde.

## 011_auditoria_actor_update

**Ahora:** todo `UPDATE` auditado, salvo la expiración automática de sesión
correlacionada por el sistema, exige un actor de aplicación antes de omitir un
cambio sólo de secretos. Se conservan la exclusión de hashes sensibles y la
supresión de filas vacías.

**Impacto frontend:** no cambia endpoints ni bodies. Refuerza que las acciones
de credenciales se ejecutan exclusivamente mediante la API autenticada y que
sus secretos nunca se leen ni se envían a bitácora.

## 012_correccion_snapshot_tuc_triestado

**Antes:** `vw_reporte_snapshot_actual` contabilizaba en el indicador `no_afecta_tuc` cualquier `proyecto_nucleo` con `afecta_tuc = false` sin verificar `tuc_revision_pendiente`. Esto absorbía indebidamente núcleos con revisión pendiente (`tuc_revision_pendiente = true`) como casos confirmados de no afectación.

**Ahora:**
- `no_afecta_tuc` requiere confirmación explícita: `pn.afecta_tuc IS FALSE AND pn.tuc_revision_pendiente IS FALSE`.
- `afecta_tuc IS NULL` representa condición desconocida/no evaluada y nunca equivale a `false`, cero ni `no_afecta_tuc`.
- Casos con revisión pendiente (`tuc_revision_pendiente = true`) no se confunden con afectación ni con no afectación.
- Se asegura conteo determinista sin duplicados mediante `count(DISTINCT pn.id_proyecto_nucleo)::bigint`.
- Se preserva el aislamiento estricto por proyecto y por entidad federativa (`GROUP BY pn.id_proyecto, e.id_entidad`).

**Impacto frontend:** transparente y correctivo en reporting (`GET /api/reportes/resumen-actual?indicador=no_afecta_tuc`). No modifica la firma de endpoints ni los schemas de respuesta (`ReporteSnapshotActualResponse`).

## 013_pagos_en_reporting

**Antes:** La vista canónica `vw_hito_seguimiento` y, por ende, `vw_reporte_avance_periodo` y `vw_dashboard_kpi`, sólo contemplaban indemnizaciones como hecho realizado a partir de `fecha_resolucion` y `avaluo_monto`. Los pagos reales registrados en la tabla `pago` no se unían a los hitos de reporting, provocando que existieran en BD y API pero estuvieran ausentes en los reportes de avance y tableros KPI.

**Ahora:**
- Se incorpora en `vw_hito_seguimiento` la unión canónica de la tabla `pago` a través de la cadena `Pago → Indemnizacion → Afectacion → ProyectoNucleo → Proyecto`.
- Cada pago activo genera un hito con:
  - `clave_hito = 'pago:' || p.id_pago`
  - `indicador = 'pagos'`
  - `fecha_programada = NULL`
  - `fecha_realizada = p.fecha_pago`
  - `monto = p.monto`
  - `programado = 0`
  - `realizado = 1`
  - `superficie_ha = NULL`
  - Dimensiones `ambito` y `tipo_cop_operativo` heredadas de `afectacion`.
- Se mantiene estricta diferenciación conceptual:
  - `Pago` es un hecho financiero concreto y no se confunde con el estatus `pagado` de `Indemnizacion` (que sin `fecha_resolucion` no periodiza ni inventa pagos).
  - No se confunde con retiros o entregas de recursos FIFONAFE.
  - No se confunde con montos declarados en convenios (`monto_100`, etc.).
  - No se confunde con el avalúo o monto resuelto de la indemnización.
- Se asegura cero duplicación frente a relaciones N:M (`ConvenioAfectacion`, `AfectacionUnidadAgraria`, `TramiteFifonafeAfectacion`).
- Se garantiza aislamiento estricto por proyecto y entidad federativa.
**Impacto frontend:** Transparente y correctivo en reporting (`GET /api/reportes/avance-periodo?indicador=pagos` y `GET /api/dashboard/kpi`). No altera firmas de endpoints ni schemas de respuesta existentes.

## Alineación API/BD Intervinientes FIFONAFE

**Antes:** `POST /api/fifonafe/{id_tramite_fifonafe}/intervinientes` no validaba en Pydantic ni en el servicio FastAPI las reglas de dominio relativas a la acreditación histórica de integrantes ORV (`id_orv_integrante`), delegando la validación exclusivamente al trigger de base de datos (`fn_validar_fifonafe_interviniente_008`). Esto provocaba que combinaciones inválidas en el payload o incompatibilidades de dominio dependieran de excepciones de bajo nivel en rollback.

**Ahora:**
- Se alinea la validación en 3 niveles: Pydantic → Servicio FastAPI → Trigger PostgreSQL.
- En Pydantic (`TramiteFifonafeIntervinienteCreate`): Si `id_orv_integrante` no es nulo, se exige obligatoriamente `id_evento_fifonafe`, respondiendo con HTTP `422 Unprocessable Entity` si falta.
- En el servicio (`add_fifonafe_interviniente` / `validate_fifonafe_interviniente`): Antes de persistir, se valida de forma controlada con HTTP `409 Conflict`:
  - Existencia y estado activo de la persona.
  - Pertenencia del evento al trámite y estado activo.
  - Existencia de fecha de negocio (`fecha_evento` o `fecha_oficio`) en el evento cuando se acredita ORV.
  - Correspondencia de la persona con el integrante ORV (`id_persona`).
  - Correspondencia del núcleo agrario del ORV con el núcleo del trámite FIFONAFE.
  - Vigencia histórica del integrante respecto a la fecha del evento.
- El trigger `trg_validar_fifonafe_interviniente_008` en PostgreSQL permanece activo e inalterado como la última barrera de integridad en base de datos.
- Esta alineación API no requirió una migración de tablas o constraints; el trigger PostgreSQL vigente permanece como última barrera. La migración 015 se limita a excluir proyectos inactivos de read-models.

**Impacto frontend:** Controlado y preventivo. Devuelve errores HTTP semánticos (`422` para payloads incompletos y `409` para violaciones de dominio) sin alterar las respuestas exitosas (`201 Created`).

## Actualización de Programación RAN Padre

**Antes:** `TramiteRan` almacenaba `fecha_programada_ingreso` únicamente al momento de creación (`POST /api/tramites-ran`). La API no exponía ningún endpoint para modificar o reprogramar la fecha de ingreso planificada, impidiendo corregir errores de captura o cambios de agenda sin recrear el trámite completo y sus eventos históricos.

**Ahora:**
- Se agrega el endpoint `PATCH /api/tramites-ran/{id_tramite_ran}`.
- Se introduce el schema `TramiteRanUpdate` con restricción estricta de campos (`model_config = ConfigDict(extra="forbid")`), permitiendo exclusivamente `fecha_programada_ingreso: date | None`.
- Permite corregir una fecha programada, asignarla si era NULL o limpiarla a NULL.
- Preserva la inmutabilidad absoluta de la identidad (`id_tramite_ran`), contexto/objetivo (`id_proyecto_nucleo`, `id_nucleo`, `id_asamblea`, `id_convenio`, `id_orv`, `referencia_expediente`) y eventos asociados.
- Cualquier campo ajeno en el cuerpo de la petición (por ejemplo `id_asamblea`, `id_convenio`, `id_orv`, `eventos`, `activo`, etc.) es rechazado con HTTP `422 Unprocessable Entity`.
- Requiere autenticación, rol de captura (`admin` u `operador`) y validación de pertenencia al proyecto mediante `require_ran_procedure_access(..., mode="capture")`, rechazando accesos no autorizados con HTTP `403 Forbidden` y trámites inexistentes con HTTP `404 Not Found`.
- Registra automáticamente la auditoría de cambio (`actualizado_en`, `actualizado_por` y registro en `bitacora` vía trigger `trg_audit_tramite_ran`).
- La reprogramación actualiza la fecha en reporting programado (`vw_reporte_avance_periodo`) sin alterar los hitos ni fechas de eventos realizados (`fecha_realizada`, `realizado`).
- Esta ampliación de API no requirió una migración de tablas o triggers; la columna definida desde 001 ya soportaba la actualización de `fecha_programada_ingreso`. La migración 015 no modifica RAN.

**Impacto frontend:** El frontend ahora puede reprogramar trámites RAN padre enviando `PATCH /api/tramites-ran/{id_tramite_ran}` con `{ "fecha_programada_ingreso": "YYYY-MM-DD" }` o `{ "fecha_programada_ingreso": null }`. Recibe el objeto `TramiteRanResponse` actualizado (HTTP 200).

## 014_convenios_colectivos_por_destino

**Antes:** El reporting de convenios colectivos (`vw_convenio_valor_declarado`, `vw_convenio_impacto`, `vw_reporte_avance_periodo`) no permitía reconstruir con precisión el desglose físico por destino de superficie cuando un mismo núcleo, afectación o convenio involucraba simultáneamente TUC, caminos, canales, drenes u otros destinos. Los endpoints previos reportaban valores declarados a nivel de instrumento o impactos por afectación, arriesgando multiplicar montos o repetir la superficie total por cada destino.

**Ahora:**
- Se publica la vista `vw_convenio_colectivo_destino` mediante la migración forward-only `014_convenios_colectivos_por_destino.sql` (con verificación del checksum de 013 y advisory lock).
- Se implementa el endpoint canónico:
  `GET /api/reportes/convenios/colectivos-destino`
  (con alias retrocompatible `GET /api/reportes/convenios/destinos`).
- La superficie física por destino se deriva estrictamente de la cadena canónica:
  `Convenio -> ConvenioAfectacion -> Afectacion -> AfectacionUnidadAgraria -> UnidadAgraria -> CatalogoOperativo(destino_superficie)`.
- Se distinguen de forma no ambigua:
  - `superficie_ha`: Superficie física afectada calculada por destino (`sum(au.superficie_afectada_ha)`).
  - `superficie_declarada_ha`: Superficie contractual declarada en el instrumento (`c.superficie_ha`).
  - `monto_declarado`: Monto económico del instrumento (`c.monto_100`). Es un atributo descriptivo **NO ADITIVO**: pertenece al convenio completo, no representa monto del destino y para agregados económicos oficiales debe contarse una sola vez por `id_convenio`.
- Si un convenio colectivo carece de unidades agrarias o sus unidades carecen de destino asignado, se reporta `destino_superficie = NULL` y `superficie_ha = NULL` (NULL nunca equivale a cero).
- Destinos repetidos en varias afectaciones del mismo convenio se consolidan sumando sus superficies.
- Múltiples destinos en un convenio conservan el monto por instrumento sin multiplicarlo ni prorratearlo arbitrariamente; no existe prorrateo por destino.
- La vista es un read-model de detalle con una fila por `id_convenio + destino_superficie`; no ejecuta agregados oficiales de cantidad. Todo consumidor que agregue estas filas debe deduplicar convenios por `id_convenio` y asambleas por `id_asamblea`, y debe contar `monto_declarado` una sola vez por convenio.
- Se garantizan filtros por `id_proyecto`, `id_entidad`, `id_proyecto_nucleo`, `id_convenio`, `id_asamblea`, `tipo_convenio`, `tipo_cop_operativo`, `destino_superficie`, `anio`, `mes`, `trimestre`.
- Aislamiento estricto por proyecto y entidad federativa mediante `authorized_project_ids` y `require_project_access`.
- Se excluyen automáticamente instrumentos individuales (`ambito = 'individual'`) y registros con baja lógica (`activo = false`).

**Impacto frontend:** Aditivo y no disruptivo. Proporciona a las interfaces de reporting y tableros de control un desglose limpio y consistente de superficies por destino para convenios colectivos, eliminando duplicaciones de importes y manteniendo la fidelidad territorial.

## 015_exclusion_proyectos_inactivos

**Antes:** Los read-models corregidos o incorporados en 012–014 exigían `ProyectoNucleo.activo`, pero podían devolver filas cuyo `Proyecto.activo` era falso. Además, una asignación activa podía aparecer en `authorized_project_ids` para un usuario no administrador aunque el proyecto estuviera inactivo.

**Ahora:** La migración forward-only 015 recrea exclusivamente `vw_reporte_snapshot_actual`, `vw_hito_seguimiento`, `vw_reporte_avance_periodo`, `vw_dashboard_kpi` y `vw_convenio_colectivo_destino`, exigiendo `Proyecto.activo IS TRUE` sin cambiar cardinalidades, fechas, montos ni semánticas de NULL. `authorized_project_ids` también une la asignación con un proyecto activo para usuarios no administradores; el administrador conserva su comportamiento global vigente sobre proyectos activos.

**Impacto frontend:** Correctivo. Un proyecto inactivo deja de aparecer en reporting y deja de ser accesible mediante una asignación activa; al reactivarlo vuelve a ser elegible conforme a las mismas reglas de acceso y baja lógica.
