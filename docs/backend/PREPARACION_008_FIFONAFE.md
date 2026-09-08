# Preparación controlada 008 — FIFONAFE

Estado: candidato no ejecutado. Base autorizada para una validación posterior: `software_pa_test`.

Checksum candidato 008 validado: `95bf328f18112933481488c59763df6a6467d8fd3db354bb7e5465c727c8f012`.

Checksum contrato SQL: `4dd46688e692226bfd0d269bac903f214c5334f1b5595b6000bc09ec9742695b`.

## Preflight real (2026-09-07)

- Rama `feature/backend-logica`; HEAD local y publicado: `53a7920507faf608d11234608c9cfc5d731ac154`.
- El worktree ya contenía cierres locales 006/007 y cambios en modelos, schemas, routers, servicios y pruebas. Se conservaron; no se hizo pull, reset, commit, push ni merge.
- `software_pa_test`, consultada como `pa_app`, contiene exactamente 001–007. 007 registra `adabd7775fb8165a1db8be04a93e7971fe207e745b410c57eb6fc76cc3a7e4f7`.
- No existen `tramite_fifonafe_interviniente`, `version_flujo` ni ledger 008.
- Los cuatro constraint triggers FIFONAFE efectivos son `ctr_fifonafe_completo_parent`, `ctr_fifonafe_completo_evento`, `ctr_fifonafe_requiere_afectacion` y `ctr_fifonafe_vinculo_requerido`; todos están habilitados, son `DEFERRABLE INITIALLY DEFERRED`. Los triggers de catálogo y auditoría están habilitados.
- Las vistas `vw_hito_seguimiento`, `vw_reporte_avance_periodo` y `vw_dashboard_kpi` pertenecen a `pa_app`; `software_pa_app` conserva SELECT/INSERT/UPDATE.

## Límite y modelo resultante

`id_tramite_fifonafe` sigue siendo la solicitud. Su N:M con afectaciones no cambia. `referencia_expediente` conserva el literal nullable y no es `UNIQUE`: ni texto, fila, parcela, núcleo ni hash bastan por sí solos para fusionar solicitudes. La identidad documental sólo puede motivar conciliación cuando el documento identifica la misma solicitud y el ProyectoNucleo/ámbito son compatibles.

`version_flujo=1` conserva el significado histórico; `version_flujo=2` rige solicitudes nuevas. La versión no aparece en Create/Update y el trigger impide cambiarla. Los legados continúan con el contrato 1. No se incluyó una operación de conversión porque no es necesaria para aplicar 008: una eventual adopción 1→2 necesitaría autorización funcional separada, motivo auditable y conciliación de evidencia; no se simula mediante PATCH o backfill.

Para versión 2:

- `programado`: actuación prevista sin recepción acreditada;
- `pendiente`: integración, trámite o diferimiento;
- `completo`: conclusión integral acreditada de una ruta aplicable;
- `cancelado`: cancelación expresa documentada;
- `otro`: situación excepcional documentada.

La ruta no se almacena por simetría. Se acredita por eventos: la administrativa exige solicitud, consulta de una misma ronda sin impedimento o dispensa soportada, resolución positiva, entrega y comprobación; para colectivo exige además una Asamblea real de retiro. La judicial exige requerimiento y cumplimiento soportados y no fabrica consulta ni resolución administrativa. Consulta concluida, resolución positiva, entrega, comprobación, indemnización y `Pago` siguen siendo identidades distintas.

`hay_conflictos` conserva `NULL/true/false`. `conflicto_impide_retiro`, ubicado en la respuesta, expresa el alcance acreditado y permite `hay_conflictos=true` con respuesta no impeditiva. Ninguno de esos valores cancela automáticamente la solicitud.

`ciclo_consulta` es nullable y positivo. La conclusión requiere envío y respuesta acreditada de la misma ronda. Los eventos sin ciclo permanecen conciliables y se informan como cobertura pendiente. `fecha_evento` se usa en actuaciones no-oficio; `fecha_oficio` conserva su significado. No se deriva ninguna de `creado_en`.

`tramite_fifonafe_interviniente` enlaza Persona con la solicitud y, opcionalmente, con evento y ORVIntegrante. Los roles son solicitante, representante, titular, beneficiario y receptor designado. ORV sólo se valida cuando se declara y su vigencia se evalúa contra la fecha del acto; una representación externa puede carecer de ORV y acreditarse mediante los requisitos/vínculos documentales. La relación no crea `Pago`, indemnización, saldo ni movimiento financiero.

## Backfill, integridad y seguridad

La incorporación de `version_flujo` usa inicialmente `DEFAULT 1`, por lo que PostgreSQL clasifica filas existentes sin ejecutar `UPDATE` ni disparar auditoría. A continuación el default cambia a 2. Todos los demás campos y la tabla de intervinientes quedan vacíos. El candidato aborta si detecta una referencia, Asamblea, ciclo, fecha, alcance de conflicto o interviniente creado por 008.

No se deshabilita ningún trigger de integridad. Como el runner no representa a una persona usuaria, se suspenden sólo `trg_audit_catalogo_operativo` y `trg_audit_requisito_documental` durante sus respectivos seeds de esquema y se reponen inmediatamente; de otro modo `fn_audit_log` rechaza correctamente la migración por falta de `app.current_user_id`. No hay DML sobre trámites o eventos existentes, de modo que no quedan eventos diferidos antes de `ALTER TABLE`. Los inserts de catálogos ocurren después de los ALTER que les conciernen. La validación documental es diferida para permitir crear el evento y su vínculo dentro de una transacción, pero se fuerza al commit. No se usa `DROP CASCADE`.

El candidato extiende sólo las listas polimórficas para el nuevo interviniente. Documento, DocumentoVinculo, expediente_requisito, Persona, ORV/ORVIntegrante y trazabilidad_fuente se reutilizan. No se agregan montos.

## Reporting y OpenAPI

La vista vigente se renombra a `vw_hito_seguimiento_007` y conserva sus filas/ACL. La nueva `vw_hito_seguimiento` es una envoltura compatible que hace `UNION ALL` con hitos v2. `fifonafe` legado no cambia. `informe_no_conflictos` sólo aparece cuando una respuesta soportada de la misma ronda declara ausencia de conflicto y ausencia de impedimento; nunca nace sólo de `hay_conflictos=false` o `acuse_fifonafe_fecha`.

Los indicadores v2 son solicitudes recibidas, consultas enviadas, respuestas acreditadas, consultas concluidas, resoluciones positivas, cancelaciones, diferimientos, entregas, comprobaciones y cumplimiento judicial. La clave usa solicitud y, para consultas, solicitud+ronda. Ninguna vista une afectaciones para agregar. `vw_fifonafe_cobertura_008` publica universo, recibidas acreditadas, eventos sin ciclo, respuestas y actuaciones sin soporte, completos y pendientes. `vw_fifonafe_indicador_institucional_008` conserva aparte la razón anual de solicitudes positivamente resueltas sobre recibidas.

OpenAPI agrega campos 008 a las respuestas/altas permitidas, mantiene `version_flujo` sólo de lectura, publica CRUD hijo mínimo de intervinientes, PATCH/baja lógica de eventos, y dos endpoints de reporting. La asociación FIFONAFE–afectación usa schema propio con `extra="forbid"`. Frontend debe tolerar los campos de respuesta nuevos y adoptar los endpoints nuevos explícitamente; no se modificó `frontend/`.

## Evidencia dirigida y regresiones

No se repitió el inventario Excel. La búsqueda dirigida confirmó los encabezados colectivos `INFORME M-Q!BQ4` (Asamblea retiro), `CC4/CC5` (informe/no. oficio FIFONAFE→DGAOPR/Representación) y `CF5` (respuesta a FIFONAFE). Los nombres autorizados aparecen en ese libro, entre otros, en `F13` Navajas, `F20:F25` San Clemente, `F26:F27` El Muerto–Ignacio Pérez, `F80:F81` San Pedrito y `F145:F149` Barrancas. El libro individual conserva repeticiones por núcleo y P-230 en `PROPUESTA!K382:L382`, `L668` y `L763`; esas filas no se convierten automáticamente en solicitudes distintas ni en una sola solicitud. Las leyendas de error siguen en revisión documental.

Pruebas preparadas:

- `008_fifonafe_evolucion_contract.sql`: ledger/checksums, neutralidad, columnas, constraints diferidos, triggers, owner/ACL, vista legada y no multiplicación;
- `008_fifonafe_evolucion_regression.sql`: escenarios sintéticos revertidos para dos solicitudes con soporte/afectación compartidos, rondas separadas, evento sin ciclo, triestado, no conflictos acreditado y separación Pago/Indemnización;
- `test_cierre_008_fifonafe_api.py`: rondas, N:M, cobertura, intervinientes, PATCH 422 atómico y baja lógica;
- `test_cierre_008_fifonafe_pre_migracion.py`: defecto API independiente del esquema 008.

En QA post-008 deben añadirse aserciones documentales de sólo lectura sobre Navajas, San Clemente, El Muerto–Ignacio Pérez, Barrancas, San Pedrito y P-230 usando las trazas/celdas ya auditadas; las contradicciones no son fixtures de éxito. Las secuencias individuales repetidas prueban deduplicación por solicitud acreditada, nunca por fila.

## Fuentes jurídicas y alcance temporal

- Reglamento de la Ley Agraria en Materia de Ordenamiento de la Propiedad Rural, arts. 77–82, texto oficial Cámara de Diputados/DOF 28-11-2012: retiro colectivo con Asamblea y documentación; retiro individual mediante solicitud e identidad/derecho; entrega directa o bancaria diferenciada.
- Normateca FIFONAFE: Lineamientos y Manual de Procedimientos de Fondos Comunes vigentes desde 07-08-2024. El Manual separa recepción, consulta, opinión, autorización, entrega, comprobación y rutas excepcionales, incluida la judicial.
- Programa Institucional FIFONAFE 2025–2030: el indicador institucional es solicitudes resueltas positivamente respecto de solicitudes recibidas.

Estas reglas gobiernan el contrato nuevo y deben aplicarse según la fecha de inicio del acto. No acreditan hechos de expedientes ni se aplican retroactivamente a los registros versión 1.

Fuentes oficiales:

- https://www.diputados.gob.mx/LeyesBiblio/regley/Reg_LAgra_MOPR.pdf
- https://www.fifonafe.gob.mx/normateca/TemasDisposiciones.asp?id=2
- https://www.fifonafe.gob.mx/m_legal/MANUAL_DE_PROCEDIMIENTOS_DE_FONDOS_COMUNES.pdf
- https://www.gob.mx/fifonafe/acciones-y-programas/fondos-comunes-uso-comun
- https://www.gob.mx/fifonafe/acciones-y-programas/fondos-comunes-uso-individual
- https://dof.gob.mx/nota_detalle_popup.php?codigo=5769859

## Aplicación y recuperación futura

Antes del runner: verificar HEAD/status/checksums, ausencia de 008/objetos parciales, sesiones incompatibles y crear un `pg_dump -Fc` único de `software_pa_test`; verificar archivo, SHA-256 y `pg_restore -l`. Aplicar sólo con el runner oficial/`pa_app`, que usa `--single-transaction` y registra el ledger al final. Luego ejecutar contrato, regresión SQL, API 008 y compatibilidad 001–007.

Si falla antes del commit, conservar log y demostrar que ledger/objetos/datos volvieron a 007; no restaurar automáticamente. Si 008 queda registrada, no editarla ni cambiar checksum: la corrección será forward-only con autorización. Restaurar `software_pa_test` desde el respaldo sólo es una recuperación controlada, autorizada y con pérdida explícitamente evaluada de datos posteriores; no se crea una tercera base.

## Validación técnica y sonda (2026-09-08)

La sonda inicial confirmó que los seeds de catálogos necesitan suspender exclusivamente sus triggers de auditoría porque el runner no aporta `app.current_user_id`; no se suspendió integridad. Una segunda sonda encontró una referencia ambigua a `id_proyecto_nucleo` en `informe_no_conflictos`, y la revisión posterior detectó que la vista base omitía `numero_oficio`. Ambas referencias quedaron calificadas/expuestas explícitamente.

La revisión semántica endureció `completo` v2: solicitud compatible con el ámbito, envío de consulta con fecha y número o soporte, respuesta documentada de la misma ronda, Asamblea colectiva de retiro celebrada y documentada, y eventos separados para resolución, entrega y comprobación. La representación ORV exige un evento fechado. Se añadieron constraint triggers diferidos sobre Asamblea y convocatoria para que retirar evidencia invalide correctamente un trámite completo.

El candidato completo y la regresión sintética terminaron con `008_REGRESSION_OK` dentro de una transacción externa y `ROLLBACK` explícito. Después de la sonda, el ledger permaneció en 001–007, no existían columnas/tablas/vistas 008, las huellas de las tres tablas FIFONAFE y de las vistas 007 coincidieron con el preflight, y todos los triggers originales siguieron habilitados. El contrato oficial no se ejecutó porque exige correctamente ledger 008; queda reservado para la aplicación definitiva.
