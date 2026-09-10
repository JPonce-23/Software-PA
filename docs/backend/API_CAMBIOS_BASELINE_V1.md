# Cambios de API respecto al Baseline V1

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

Vigentes: 001, 002, 003, 004, 005. Siguiente migración: 006.
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
