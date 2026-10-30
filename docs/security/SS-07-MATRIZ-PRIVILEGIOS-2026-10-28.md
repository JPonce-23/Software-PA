# SS-07: matriz de privilegios necesarios y evidencia

Fecha: 2026-10-28. `dev`, SHA `683ff75613768de28a7127c7e33a6e2ef4fc40ff` más remediaciones locales preservadas. **No contiene permisos efectivos observados; todos siguen pendientes QA.** [Informe](SS-07-ETAPA1-AUDITORIA-PRIVILEGIOS-2026-10-28.md), [plan](SS-07-PLAN-HARDENING-POSTGRESQL.md), [inventario completo](ss07/inventario-estatico.json).

S=SELECT; I=INSERT; U=UPDATE; —=no necesidad demostrada de esa operación, **no prueba de revocación efectiva**. L=requiere UPDATE para lock de fila, aunque no se observe edición por API de ese catálogo. †=inserción indirecta por trigger invoker. S*=lectura de catálogo/relación/dependencias; algunas proyecciones se cargan por relaciones ORM y la necesidad exacta debe medirse en QA. Una fila S/I/U es un presupuesto candidato del módulo de gestión, no una concesión irrestricta por columna ni una prueba de que cada endpoint use las tres.

Las FKs, triggers invoker, relaciones eager, RETURNING y locks forman parte de las necesidades. Los enlaces de evidencia señalan una referencia, no toda la cadena; el JSON contiene el resto. No convertir esta matriz en REVOKE automatizado sin QA y revisión de auxiliares.

## Matriz por tabla declarada

Las65 tablas permanentes declaradas se enumeran individualmente; no se afirma que todas existan así en el destino. DELETE físico, TRUNCATE, REFERENCES y TRIGGER no se necesitan para las bajas lógicas HTTP inspeccionadas. UPDATE de un flag activo no es DELETE. Migrador/owner tienen una matriz distinta, más abajo.

| Tabla | SELECT | INSERT | UPDATE | DELETE | Evidencia y precisión |
|---|---|---|---|---|---|
| `actividad_campo` | S | I | U | — | `backend/app/routers/domain.py:740`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `afectacion` | S | I | U | — | `backend/app/routers/domain.py:925`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `afectacion_unidad_agraria` | S | I | U | — | `backend/app/routers/domain.py:2037`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `asamblea` | S | I | U | — | `backend/app/routers/domain.py:1068`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `asamblea_convocatoria` | S | I | U | — | `backend/app/routers/domain.py:1109`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `bitacora` | S | — | — | — | `backend/app/services/audit.py:79`; Lectura auditoría; INSERT indirecto SECURITY DEFINER, no runtime directo (009) |
| `catalogo_alias_territorial` | S* | — | — | — | `backend/db/migrations/001_baseline_v1.sql:1714`; Catálogo/proyección o flujo auxiliar: I/U de bootstrap/importación no se asignan automáticamente a FastAPI |
| `catalogo_operativo` | S | I | U | — | `backend/app/routers/domain.py:95`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `catalogo_operativo_alias` | S* | — | — | — | `backend/db/migrations/001_baseline_v1.sql:1789`; Catálogo/proyección o flujo auxiliar: I/U de bootstrap/importación no se asignan automáticamente a FastAPI |
| `catalogo_tipo_documento` | S | — | L | — | `backend/app/services/documents.py:80`; documents.require_document_type usa FOR SHARE; no revocar U sin resolver lock |
| `convenio` | S | I | U | — | `backend/app/routers/domain.py:1315`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `convenio_afectacion` | S | I | U | — | `backend/app/routers/domain.py:1315`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `convenio_compareciente` | S | I | U | — | `backend/app/routers/domain.py:1366`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `derecho_via_proyecto` | S | I | U | — | `backend/app/routers/reporting.py:781`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `documento` | S | I | U | — | `backend/app/routers/documents.py:59`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `documento_version` | S | I | — | — | `backend/app/routers/documents.py:166`; Append-only/versiones; no UPDATE funcional observado, confirmar triggers/ACL/RETURNING en QA |
| `documento_vinculo` | S | I | U | — | `backend/app/routers/documents.py:59`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `entidad_federativa` | S* | — | — | — | `backend/app/routers/domain.py:47`; Catálogo/proyección o flujo auxiliar: I/U de bootstrap/importación no se asignan automáticamente a FastAPI |
| `estado_autenticacion_usuario` | S | I† | U | — | `backend/app/routers/users.py:50`; INSERT por trigger de usuario; UPDATE por login/recuperación, invoker requiere permisos |
| `evento_acceso` | S | I | — | — | `backend/app/services/authentication.py:71`; Append-only/versiones; no UPDATE funcional observado, confirmar triggers/ACL/RETURNING en QA |
| `expediente_requisito` | S | I | U | — | `backend/app/routers/domain.py:1690`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `importacion_archivo` | S | I | U | — | `backend/app/routers/geospatial_imports.py:43`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `importacion_conciliacion_ciclo` | S | I | U | — | `backend/app/routers/geospatial_imports.py:292`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `importacion_conciliacion_resultado` | S | I | — | — | `backend/app/services/gis_reconciliation.py:174`; Append-only/versiones; no UPDATE funcional observado, confirmar triggers/ACL/RETURNING en QA |
| `importacion_feature` | S | I | U | — | `backend/app/routers/geospatial_imports.py:200`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `importacion_feature_candidato` | S | I | U | — | `backend/app/routers/geospatial_imports.py:251`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `importacion_feature_decision` | S | I | — | — | `backend/app/routers/geospatial_imports.py:265`; Append-only/versiones; no UPDATE funcional observado, confirmar triggers/ACL/RETURNING en QA |
| `importacion_tabular` | S* | — | — | — | `backend/db/migrations/001_baseline_v1.sql:2397`; Catálogo/proyección o flujo auxiliar: I/U de bootstrap/importación no se asignan automáticamente a FastAPI |
| `importacion_tabular_celda` | S* | — | — | — | `backend/db/migrations/001_baseline_v1.sql:2428`; Catálogo/proyección o flujo auxiliar: I/U de bootstrap/importación no se asignan automáticamente a FastAPI |
| `indemnizacion` | S | I | U | — | `backend/app/routers/domain.py:1739`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `municipio` | S* | — | — | — | `backend/app/routers/domain.py:58`; Catálogo/proyección o flujo auxiliar: I/U de bootstrap/importación no se asignan automáticamente a FastAPI |
| `nucleo_agrario` | S | I | U | — | `backend/app/routers/domain.py:202`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `orv` | S | I | U | — | `backend/app/routers/domain.py:556`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `orv_integrante` | S | I | U | — | `backend/app/routers/domain.py:637`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `padron_historial` | S | I | U | — | `backend/app/routers/domain.py:694`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `pago` | S | I | U | — | `backend/app/routers/domain.py:1785`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `parcela` | S | I | U | — | `backend/app/routers/domain.py:791`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `parcela_titular` | S | I | U | — | `backend/app/routers/domain.py:861`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `perfil_mapeo_importacion` | S* | — | — | — | `backend/db/migrations/001_baseline_v1.sql:2899`; Catálogo/proyección o flujo auxiliar: I/U de bootstrap/importación no se asignan automáticamente a FastAPI |
| `persona` | S | I | U | — | `backend/app/routers/domain.py:861`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `proyecto` | S | I | U | — | `backend/app/routers/domain.py:146`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `proyecto_configuracion_gis` | S | I | U | — | `backend/app/services/gis_reconciliation.py:40`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `proyecto_nucleo` | S | I | U | — | `backend/app/routers/domain.py:207`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `proyecto_nucleo_geometria` | S | I | U | — | `backend/app/routers/reporting.py:792`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `proyecto_nucleo_referencia` | S | I | U | — | `backend/app/routers/domain.py:373`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `proyecto_nucleo_responsable` | S | I | U | — | `backend/app/routers/domain.py:428`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `proyecto_parcela_geometria` | S | I | U | — | `backend/app/routers/reporting.py:830`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `requisito_documental` | S* | — | — | — | `backend/app/routers/domain.py:1674`; Catálogo/proyección o flujo auxiliar: I/U de bootstrap/importación no se asignan automáticamente a FastAPI |
| `revision_cambio_gis` | S | I | — | — | `backend/app/services/gis_history.py:144`; Append-only/versiones; no UPDATE funcional observado, confirmar triggers/ACL/RETURNING en QA |
| `revision_cambio_gis_decision` | S | I | — | — | `backend/app/services/gis_read_models.py:148`; Append-only/versiones; no UPDATE funcional observado, confirmar triggers/ACL/RETURNING en QA |
| `schema_migrations` | S | — | — | — | `backend/db/migrations/001_baseline_v1.sql:3819`; Health/main.py: SELECT max(version); runner requiere S/I como migrador |
| `seguimiento_evento` | S | I | U | — | `backend/app/routers/domain.py:990`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `sesion_usuario` | S | I | U | — | `backend/app/auth.py:46`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `tramite_fifonafe` | S | I | U | — | `backend/app/routers/domain.py:1483`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `tramite_fifonafe_afectacion` | S | I | U | — | `backend/app/services/domain.py:1229`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `tramite_fifonafe_evento` | S | I | U | — | `backend/app/routers/domain.py:1545`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `tramite_fifonafe_interviniente` | S | I | U | — | `backend/app/routers/domain.py:1616`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `tramite_ran` | S | I | U | — | `backend/app/routers/domain.py:1201`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `tramite_ran_evento` | S | I | U | — | `backend/app/routers/domain.py:1281`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `trazabilidad_fuente` | S | I | — | — | `backend/app/routers/documents.py:108`; Append-only/versiones; no UPDATE funcional observado, confirmar triggers/ACL/RETURNING en QA |
| `trazo_proyecto` | S | I | U | — | `backend/app/routers/domain.py:1827`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `unidad_agraria` | S | I | U | — | `backend/app/services/convenio_reports.py:122`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `unidad_agraria_titular` | S | I | U | — | `backend/app/routers/domain.py:1974`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `usuario` | S | I | U | — | `backend/app/auth.py:46`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |
| `usuario_proyecto` | S | I | U | — | `backend/app/routers/users.py:206`; Captura/gestión/baja lógica o GIS; presupuesto candidato por operación, validar rutas y dependencias en QA |

### Precisiones críticas de la matriz

- `catalogo_tipo_documento`: `require_document_type` usa `with_for_update(read=True)`/FOR SHARE. Los locks de fila requieren un privilegio UPDATE además de SELECT; retirar todo UPDATE rompe ese flujo. Evaluar privilegio por columna, cambio del protocolo o función controlada en una autorización futura, con pruebas; no aplicar el simple rótulo “catálogo sólo lectura”.
- `bitacora`: runtime no debe insertar/actualizar/borrar directamente. El propietario de fn_audit_log necesita INSERT y capacidad sobre su secuencia; el invocador del trigger y su owner no se confunden. Su lectura por API de auditoría sigue siendo necesaria.
- `evento_acceso`, `documento_version` y trazabilidad: S/I se justifican por lectura/alta. Los triggers inmutables no son sustituto de ACL para reducir U/D/TRUNCATE. No afirmar que hoy no exista UPDATE sólo porque el trigger lo rechaza.
- `estado_autenticacion_usuario`: el alta de usuario dispara inicialización; esa inserción indirecta y las validaciones/locks de login deben conservarse. No quitar I sin demostrar cambio seguro de contexto de ejecución.
- `revision_cambio_gis`, decisiones y resultados: conservar S/I y revocaciones explícitas025/026.030 evita pedir UPDATE para bloquear revisión append-only; no deshacerlo con un grant general.
- `importacion_feature`, candidatos, geometrías y ciclo: updates de estado/es_vigente/resumen siguen siendo funcionales aunque payload/historia estén protegidos. Append-only no se aplica a toda tabla GIS indiscriminadamente.
- `importacion_tabular*`, perfiles y alias: hay modelos, FKs/lecturas y procesos auxiliares. No se acreditó una necesidad general de escritura del servicio HTTP para todos ellos; revisar consumidor/importador antes de mantener o revocar I/U.
- `schema_migrations`: SELECT sí es necesario por `/health`; INSERT del runner es exclusivo del migrador. UPDATE de lineage existe en herramienta administrativa separada, no justifica UPDATE del runtime.

## Vistas y vistas materializadas

El inventario léxico detecta21 nombres de vistas; hay redefiniciones y recreaciones. Algunas son auxiliares de otras vistas, no consumidores HTTP directos. No existen CREATE MATERIALIZED VIEW detectados en las30 migraciones; si QA descubre una materializada o una vista adicional, se registra como deriva a revisar, no se elimina ni se concede refresh automáticamente.

| Vista declarada | Permiso candidato | Última declaración encontrada, no catálogo efectivo |
|---|---|---|
| `vw_convenio_cobertura_impacto` | SELECT candidato; sin I/U/D de API acreditados | `backend/db/migrations/007_convenios_impactos_precision.sql:646` |
| `vw_convenio_colectivo_destino` | SELECT candidato; sin I/U/D de API acreditados | `backend/db/migrations/015_exclusion_proyectos_inactivos.sql:126` |
| `vw_convenio_impacto` | SELECT candidato; sin I/U/D de API acreditados | `backend/db/migrations/007_convenios_impactos_precision.sql:575` |
| `vw_convenio_tipo_cop_operativo` | SELECT candidato; sin I/U/D de API acreditados | `backend/db/migrations/002_cierre_fuentes_excel.sql:94` |
| `vw_convenio_valor_declarado` | SELECT candidato; sin I/U/D de API acreditados | `backend/db/migrations/007_convenios_impactos_precision.sql:546` |
| `vw_dashboard_kpi` | SELECT candidato; sin I/U/D de API acreditados | `backend/db/migrations/015_exclusion_proyectos_inactivos.sql:114` |
| `vw_fifonafe_cobertura_008` | SELECT candidato; sin I/U/D de API acreditados | `backend/db/migrations/008_fifonafe_evolucion_forward_only.sql:541` |
| `vw_fifonafe_consulta_008` | SELECT candidato; sin I/U/D de API acreditados | `backend/db/migrations/008_fifonafe_evolucion_forward_only.sql:437` |
| `vw_fifonafe_evento_acreditado_008` | SELECT candidato; sin I/U/D de API acreditados | `backend/db/migrations/008_fifonafe_evolucion_forward_only.sql:431` |
| `vw_fifonafe_hito_008` | SELECT candidato; sin I/U/D de API acreditados | `backend/db/migrations/008_fifonafe_evolucion_forward_only.sql:455` |
| `vw_fifonafe_indicador_institucional_008` | SELECT candidato; sin I/U/D de API acreditados | `backend/db/migrations/008_fifonafe_evolucion_forward_only.sql:552` |
| `vw_gis_parcela_proyecto` | SELECT candidato; sin I/U/D de API acreditados | `backend/db/migrations/025_conciliacion_gis_proyecto.sql:51` |
| `vw_hito_seguimiento` | SELECT candidato; sin I/U/D de API acreditados | `backend/db/migrations/015_exclusion_proyectos_inactivos.sql:32` |
| `vw_hito_seguimiento_007` | SELECT candidato; sin I/U/D de API acreditados | `backend/db/migrations/016_normalizacion_convenio_superficie_adicional.sql:308` |
| `vw_orv_estado` | SELECT candidato; sin I/U/D de API acreditados | `backend/db/migrations/001_baseline_v1.sql:7789` |
| `vw_proyecto_nucleo_resumen` | SELECT candidato; sin I/U/D de API acreditados | `backend/db/migrations/001_baseline_v1.sql:7812` |
| `vw_reporte_avance_periodo` | SELECT candidato; sin I/U/D de API acreditados | `backend/db/migrations/015_exclusion_proyectos_inactivos.sql:99` |
| `vw_reporte_convenio_impacto_periodo` | SELECT candidato; sin I/U/D de API acreditados | `backend/db/migrations/007_convenios_impactos_precision.sql:628` |
| `vw_reporte_snapshot_actual` | SELECT candidato; sin I/U/D de API acreditados | `backend/db/migrations/015_exclusion_proyectos_inactivos.sql:20` |
| `vw_revision_cambio_gis_estado` | SELECT candidato; sin I/U/D de API acreditados | `backend/db/migrations/026_historia_cambios_gis.sql:264` |
| `vw_seguimiento_estado_actual` | SELECT candidato; sin I/U/D de API acreditados | `backend/db/migrations/004_seguimiento_funcional_excel.sql:176` |

No se observa necesidad de INSERT/UPDATE/DELETE sobre vistas para los reportes. Baseline y008 incluyen grants amplios sobre algunas vistas; una futura restricción debe verificar dependencias, reglas, security_invoker/security_barrier y permisos del propietario. SELECT de una vista y derechos sobre sus tablas no son intercambiables sin analizar su modo de ejecución. Q06/Q07/Q12/Q16 cubren metadatos y privilegios de ambas.

## Secuencias y tipos

| Uso | Necesidad candidata | Evidencia / cautela |
|---|---|---|
| PK serial con nextval/default | USAGE en su secuencia; SELECT sólo si existe consumidor que lo necesita | [Funciones de secuencia PG15](https://www.postgresql.org/docs/15/functions-sequence.html). USAGE o UPDATE permite nextval; UPDATE permite setval y no está justificado para runtime |
| Identity | Verificar comportamiento específico de INSERT generado, secuencia y funciones/trigger con identidad real | No asumir que todos los identity requieren exactamente el mismo grant explícito que serial. Q10 usa pg_depend para pertenencia; probar INSERT/RETURNING sin consultar valores reales |
| Secuencia bitacora | Privilegios del owner definer al escribir auditoría, no grants directos universales al runtime | No eliminar permisos del owner de auditoría al reducir los del login |
| Catálogos cargados por migrador/importador | USAGE/SELECT/UPDATE de secuencia según operación administrativa real | No trasladar setval/reset/ownership al contrato FastAPI |
| geometry/geography y tipos PostGIS | USAGE de tipos y schema para expresiones usadas; EXECUTE sobre firmas necesarias | No se instala/actualiza extensión con runtime. Cobertura por Q15/Q19 y pruebas PostGIS |

Se identifican59 nombres de secuencia explícitos o referidos en grants, enumerados con fuente en el JSON. `seguimiento_evento.id_seguimiento_evento` y `catalogo_tipo_documento.id_tipo_documento` declaran identity sin nombre explícito capturado: su asociación/nombre real queda a Q10. No se fabrican grants usando concatenación de nombre de tabla/columna. No leer `last_value`, ni ejecutar nextval/setval/currval en el verificador.

## Funciones y controles indirectos

| Familia | EXECUTE / datos requeridos | Riesgo de revocar sin análisis |
|---|---|---|
| `fn_persona_tiene_relaciones_activas` | Invocación directa desde access.py/domain.py; EXECUTE y dependencias SELECT | Rompe aislamiento/edición de persona si se omite; no reemplazar por bypass de autorización |
| `fn_audit_log` SECURITY DEFINER | Trigger instalado; propietario confiable, INSERT bitacora, lectura de contexto/relaciones y secuencia según definición | Auditar roles/owner/search_path; no conceder INSERT directo bitacora como “solución” a un fallo |
| Validadores `fn_validar_*`, `fn_auth_*`, `fn_gis_*` | Mayormente trigger invoker: lecturas de relaciones/catálogos y locks; inicialización auth puede insertar y revocación modificar sesiones | Restringir SELECT/DML sin conservar el cuerpo invoker puede romper una operación válida. Verificar EXECUTE al crear triggers y ejecución instalada en QA, sin asumir que revocarlo desactiva por sí solo un trigger |
| Helpers `fn_opcion_catalogo_valida`, `fn_objetivo_*`, `fn_convenio_*`, normalización | Usados desde vistas/constraints/validadores; resolución/firma y permisos del contexto efectivo | No son permisos administrativos sólo por llamarse fn_; trazar dependencia antes de revocar |
| PostGIS | ST_GeomFrom*, ST_As*, ST_Transform, SRID, validación, Force2D, Zmflag, Area, Intersects/Intersection, Equals, Collect/UnaryUnion y otras coincidencias del inventario | No reducir a una lista de nombres sin firmas y dependencias. Confirmar funciones sobre geometry/geography, operadores/casts y vistas de extensión; un grant `ALL FUNCTIONS public` abarca más de lo justificado |
| Builtins pg_catalog | Funciones SQL agregadas/texto/JSON, set_config de actor, txid_current y advisory locks usados por API/triggers | No revocar EXECUTE indiscriminadamente en pg_catalog para intentar impedir actor elegible; la confianza del login compartido requiere otro modelo si se quiere cambiar |
| Rutinas de extensión/admin/otros schemas | No hay necesidad general justificada para runtime | Q11/Q15/Q21, roles predefinidos y propiedad. Un resultado EXECUTE no demuestra que toda firma sea explotable con los demás controles presentes |

El inventario registra78 **nombres** de función de migraciones, con todos sus sitios de declaración; no deduplica por firma SQL como un catálogo. Las46 coincidencias de funciones/expresiones de aplicación incluyen construcciones SQL, por lo que no son una lista lista para GRANT. Q11 usa OID/proargtypes/prorettype para distinguir rutinas en QA sin imprimir su cuerpo.

## Roles × objetos de administración

| Objeto/capacidad | Runtime / software_pa_app | Migrador | Owner/admin |
|---|---|---|---|
| Base de aplicación | CONNECT; CREATE no; TEMP sólo dependencia auxiliar a resolver | CONNECT, TEMP para migraciones que lo usan; DDL bajo identidad autorizada | Administración según procedimiento |
| Schema public | USAGE; CREATE no justificado | USAGE/CREATE/ownership para cambios aprobados | Owner de schema confiable; proteger PUBLIC |
| Tablas de negocio | Matriz S/I/U, sin D/TRUNCATE/REFERENCES/TRIGGER generales | DDL/backfills autorizados, no tráfico HTTP | Recuperación/administración auditadas |
| schema_migrations | S por health; sin I/U/D/TRUNCATE | S/I por runner; U sólo reparación especial autorizada | Control de historial, sin sobrescritura casual |
| Funciones/triggers/vistas | Uso mínimo; sin propiedad ni ALTER/DROP/creación | Crear/reemplazar controles bajo owner correcto | Revisión de SECURITY DEFINER/namespace |
| Extensiones | Uso acotado de objetos/tipos, no CREATE/UPDATE | Según trusted/untrusted y privilegios necesarios, normalmente paso admin separado | PostGIS/btree_gist, con revisión de versión/owner |
| Roles y defaults | Sin CREATEROLE, ADMIN OPTION o grants a terceros justificados | Sin administración global por defecto; puede requerir ejecución controlada como owner para DDL/defaults | Provisionar/reasignar ownership y defaults por creador autorizado |
| Objetos fuera de aplicación | Ninguno salvo plataforma/dependencias justificadas | Sólo alcance del cambio aprobado | No usar SUPERUSER como requisito habitual de la API |

Ninguna celda “no” acredita que el destino ya lo deniegue. Herencia, SET ROLE posible, grants directos, PUBLIC, ownership y permisos de columna deben cruzarse. No se crean roles PostgreSQL para admin/operador/visualizador/geografo en esta intervención ni se implementa RLS.
