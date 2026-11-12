# Cobertura de pruebas de seguridad

Fecha: 2026-10-27. `dev` / `683ff75613768de28a7127c7e33a6e2ef4fc40ff`. Sólo diagnóstico.

## Evidencia y criterios

**Existencia de una prueba no implica aprobación actual.** Se inspeccionaron fuentes y fixtures antes de decidir ejecución. Las suites bajo backend/tests importan conftest.py, que exige APP_ENV=test, DB_NAME=software_pa_test y TEST_ALLOW_DATABASE=software_pa_test antes de importar app. Es una protección útil, pero no hace la suite puramente en memoria: SessionLocal conecta a PostgreSQL, puede crear cuenta admin QA y sesiones, y varias fixtures hacen commits. Las transacciones externas/savepoints de algunas pruebas no eliminan todos los efectos de las suites que usan conexiones separadas. No se ejecutó pytest ni pytest --collect-only (también importa conftest).

La raíz de cargas de pytest se redirige a tmp_path, y hay comprobaciones de current_database para la cuenta QA. Aun así se necesita una BD desechable y autorización específica de esa fase. Los contratos SQL pueden hacer INSERT/UPDATE o DDL denegado intencionalmente aunque terminen en ROLLBACK: **no son comandos de inspección del servidor**.

Tipos de evidencia: C = fuente actual; D = QA/documentación histórica; A = prueba aislada actual. No hay evidencia actual de DB/API/servidor real.

## Controles, escenarios y vacíos

| Control / riesgo | Prueba existente | Escenarios observados | Evidencia | Vacíos negativos o adicionales | Dependencias / ejecución segura aquí |
|---|---|---|---|---|---|
| Sesión y CSRF / SS-04 | test_auth_rbac.py | Anónimo 401, cookie/CSRF, roles y filtro antes de paginar | C; no reejecutada | Todos los métodos/Origin ausente/cruzado, múltiples sesiones, expiración real y absoluta, bloqueo distribuido, revocación concurrente y cuota de eventos | PostgreSQL vía conftest; escribe cuentas/sesiones/negocio; NO |
| Contraseñas / SS-04 | test_credential_management.py | >72 bytes, política en alta/cambio/reset, correo y revocación, cuenta inactiva/bloqueada y auto-reset | C | Timing de enumeración, solicitudes simultáneas con revocación, contraseñas comprometidas/MFA si se adoptan | PostgreSQL y sesiones; NO |
| Persona y alcance | test_person_project_access.py | Caminos de relaciones, edición de persona compartida con todos los proyectos, huérfanos, referencias ocultas, alcance al cambiar y concurrencia | C | Ampliar combinaciones de PN/núcleo compartidos, recursos inactivos y todos los PATCH de referencias | PostgreSQL, usuarios y relaciones; NO |
| Gestión GIS y 030 | test_gis_management_rbac.py | Inventario completo de gestión, anónimo/otros roles denegados, geógrafo sin asignación, inactivos, IDs ajenos, histórico y trigger directo | C | Casos de parser sin secretos/red, quotas, headers de proxy/consumo, actor autenticado independientemente del principal SQL | PostgreSQL; prueba directa de rol/trigger y sesiones; NO |
| Importación GIS / SS-02/03 | test_geospatial_imports.py; test_ddv_gpkg_imports.py; test_gis_preflight_024.py; test_gis_confirmation_024.py | Formatos y CRS, mapping, confirmación/idempotencia, compatibilidad legacy y validaciones GPKG | C | ZIP Slip/symlink/archivo especial en corpus sintético, entradas numerosas/ratio, driver hostil disfrazado, GeoJSON gigante, límite de vértices, unidades de GDAL y cancelación global | PostgreSQL + GDAL/subprocesos + archivos temporales; NO |
| Concurrencia GIS | test_gis_concurrency_026.py; test_gis_history_regressions.py | Ciclos concurrentes, deduplicación, una geometría vigente, confirmación/revisión idempotente | C | Matar worker, caída de conexión/disco y recuperación; lectura concurrente con cuotas alcanzadas | PostgreSQL, conexiones concurrentes y fixtures GPKG; NO |
| Objetivos documentales / SS-05/06/12 | test_document_targets_039.py; test_documents_dashboard.py; test_document_type_catalog.py | Varios objetivos, 404/422/403, permisos por rol, actividad, bajas, versiones, catálogo y consolidado | C | Dos proyectos y documento compartido, modificación/baja global, ACL de versión antigua, firma/MIME falsos, contenido activo, colisión de versiones/crash, integridad física | PostgreSQL y archivos, algunas dependencias simuladas pero conftest real; NO |
| Auditoría / SS-07/10 | test_audit_api.py; tests runtime SQL | Sólo admin, sanitización, filtros, append-only, heartbeat y evento correlacionado, actor obligatorio | C | Parámetros en logs del proceso, shadowing pg_temp, suplantación de actor con SQL runtime y permisos heredados reales | PostgreSQL con escrituras y pruebas de privilegios; NO |
| API de reportes / SS-11 | test_convenio_general_report.py; test_convenio_report_connections.py; test_report_references_performance.py | Acotación de reporte, conexiones/snapshot, lotes, referencias/paginación y métricas | C | Límite completo de otras consultas/mapas/CSV, memoria, cancelación y fórmulas de campos controlables | PostgreSQL; scripts de setup/Compose existen; NO |
| Mapa GIS publicado / rol | tests/frontend-ssalfer/map-gis-rbac.cjs | Publicado para lectores, internas denegadas a operador/visualizador, histórico para admin/geógrafo, cambio de proyecto descarta preview | A; archivo aprobado | No prueba endpoint HTTP ni XSS de tooltip publicado | Node builtin, DOM/API dobles; SÍ, ejecutada |
| Inicio de gestión por rol | tests/frontend-ssalfer/gis-bootstrap-rbac.cjs | Espera sesión; denegación no hace DOM/API; inicia admin/geógrafo | A; archivo aprobado | No prueba servidor ni contenido hostil | Node builtin y VM; SÍ, ejecutada |
| Dashboard denegado | tests/frontend-ssalfer/dashboard-authorization.cjs | No consulta ni inicializa DOM al denegar pantalla, distintos órdenes de sesión/DOM | A; archivo aprobado | No acredita filtros SQL ni autorización de todos los endpoints | Node builtin y VM; SÍ, ejecutada |
| Navegación/roles | deploy/qa-roles-2026-10-19.cjs; qa-roles-login; qa-roles-proyecto; backend/qa_roles_readonly.py | Documento reporta 199 controles de pantallas, 8 recorridos y 31 controles servidor con persistencia simulada | D | No equivale a todos los casos de negocio/API | Node QA puede usar navegador/API; qa_roles_readonly abre DB y consulta registros reales en READ ONLY; NO aquí |
| Sesiones de frontend | deploy/qa-sesiones-2026-10-21.cjs; qa-sesiones-integracion-2026-10-21.cjs | 23 casos documentados de API simulada y cuatro roles de copia QA; 401/403, logout único, formularios/pestañas | D | Documento excluye esperar 30 min/8 h; no regresión completa ni reproducción del incidente histórico | Segundo script crea/cierra sesiones reales QA; ninguno reejecutado aquí |
| XSS SS-01 | AIS-01 actual; no regresión específica existente localizada para este tooltip | Método real minificado de Leaflet entrega HTML inerte al setter innerHTML simulado | A | Navegador, almacenamiento real sintético, interacción y CSP final; no basta el mock para afirmar ejecución de JS | Sin API/DB/navegador ni escritura; SÍ |
| Unidades GIS SS-03 | AIS-02 actual | Extrae y ejecuta _gdal_environment con os simulado: valor 104857600 frente a 100 MB esperados | A | Aplicar límite real con versión GDAL efectiva en sandbox | Sin subproceso ni BD; SÍ |
| Documento compartido SS-05 | AIS-03 actual | Funciones reales extraídas con DB simulada: un vínculo autoriza y baja afecta a ambos | A; estado de riesgo sigue Potencial por política | Resolver política funcional y probar A/B con versiones en QA | Sin API/DB/archivos; SÍ |

## Ejecuciones actuales y resultados

| ID | Comprobación | Resultado | Lo que no acredita |
|---|---|---|---|
| META | Git status/rev-parse/remote/branch de sólo lectura | Dev limpio; SHA de referencia exacto | Frescura GitHub, rulesets o producción |
| SYN-PY | ast.parse de los 129 archivos .py versionados | 129 sin SyntaxError | Tipos, dependencias resueltas o seguridad de lógica |
| SYN-JS | node --check sobre 88 JS propios SSALFER, vendor excluido | 88 sin error | XSS, DOM, navegador, backend |
| NODE-RBAC | Tres archivos Node enumerados abajo | Runner: 3 unidades aprobadas, 0 fallos | Autenticación de servidor/BD o todas las 208 operaciones |
| AIS-01 | Sink real Leaflet aislado | PASS; HTML llega sin escapar a innerHTML | Explotación end-to-end o acceso a datos de víctima |
| AIS-02 | Entorno GDAL aislado | PASS; constata error de unidad | Denegación de servicio medida |
| AIS-03 | Access/delete documento aislados | PASS; confirma semántica global | Filtración o violación de una política compartida aún no aprobada |
| SECRET | Patrones locales sin emitir valores | 2317 blobs de texto <=2 MB de historia alcanzable, 0 candidatos de claves privadas/GitHub/AWS | Reflogs, inalcanzables, OCR, binarios, formatos no cubiertos o credenciales activas |

Comando de pruebas existentes ejecutado tras inspeccionar los tres scripts y su helper source.cjs: sólo leen fuentes, usan VM/DOM/API dobles y no conectan ni escriben archivos.

```sh
node --test tests/frontend-ssalfer/map-gis-rbac.cjs tests/frontend-ssalfer/gis-bootstrap-rbac.cjs tests/frontend-ssalfer/dashboard-authorization.cjs
```

Salida resumida: tests 3, pass 3, fail 0. El runner agrupa por archivo; no se transforma ese número en 208 endpoints aprobados. Los tres archivos definen internamente distintos escenarios; el resultado se reporta tal como lo emitió la herramienta.

### AIS-01: reproducción del sink con marca inerte

Ejecutado desde raíz con Node ya instalado. No carga toda Leaflet ni un navegador: sólo compila el método previamente inspeccionado, con objeto DOM mínimo y sin evento activo.

```js
const fs = require('fs'), assert = require('assert');
const s = fs.readFileSync('frontend-ssalfer/js/vendor/leaflet-1.9.4/leaflet.js', 'utf8');
const start = s.indexOf('_updateContent:function()') + '_updateContent:'.length;
const end = s.indexOf(',_updatePosition:', start);
assert(start > 0 && end > start);
const method = Function('return (' + s.slice(start, end) + ')')();
let sink;
const marker = '<b data-audit>marca inerte</b>';
method.call({_content: marker, _contentNode: {set innerHTML(v) {sink = v;}}, fire() {}});
assert.strictEqual(sink, marker);
```

Se conecta estáticamente con ParcelaUpdate → reporting.project_map → agregarFeature.bindTooltip. No guardar payloads ejecutables en un sistema real. Prueba posterior: marcar texto literal y verificar ausencia de nodos/eventos en navegador desechable.

### AIS-02: reproducción de unidades sin GDAL

```python
import ast, pathlib, types
p = pathlib.Path('backend/app/services/gis_ingestion.py')
f = next(n for n in ast.parse(p.read_text()).body
         if isinstance(n, ast.FunctionDef) and n.name == '_gdal_environment')
ns = {'os': types.SimpleNamespace(environ={}, getenv=lambda k, d: d)}
exec(compile(ast.Module(body=[f], type_ignores=[]), str(p), 'exec'), ns)
assert ns['_gdal_environment']()['OGR_GEOJSON_MAX_OBJ_SIZE'] == '104857600'
```

El assert confirma el valor actual erróneo; no es una prueba que deba pasar tras corregirlo. La [documentación del driver](https://gdal.org/en/stable/drivers/vector/geojson.html) expresa la opción en MB; no confundir límite de bytes de carga con límite de feature/driver.

### AIS-03: comportamiento compartido, sin aprobar la política

```python
import ast, pathlib, types
class Col:
    def __eq__(self, other): return None
    def is_(self, other): return None
class E(Exception):
    def __init__(self, status_code=403, detail=''): self.status_code = status_code
Doc = type('Documento', (), {'id_documento': Col(), 'activo': Col()})
Link = type('DocumentoVinculo', (), {'id_documento': Col(), 'activo': Col()})
links = [types.SimpleNamespace(entidad_tipo='proyecto_nucleo', entidad_id=i, activo=True)
         for i in [1, 2]]
doc = types.SimpleNamespace(activo=True)
class Q:
    def __init__(self, model): self.model = model
    def filter(self, *args): return self
    def first(self): return doc
    def all(self): return links
class DB:
    def query(self, model): return Q(model)
def target(db, user, kind, identifier, mode='read'):
    if identifier != 1: raise E()
    return 10
ns = {'Session': object, 'AccessMode': str,
      'models': types.SimpleNamespace(Usuario=object, Documento=Doc, DocumentoVinculo=Link),
      'HTTPException': E, 'require_document_target_access': target, '_forbidden': lambda: E()}
def load_function(path, name):
    p = pathlib.Path(path)
    f = next(n for n in ast.parse(p.read_text()).body
             if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[f], type_ignores=[]), str(p), 'exec'), ns)
load_function('backend/app/services/access.py', 'require_document_access')
assert ns['require_document_access'](DB(), object(), 1, mode='capture') is doc
ns.update(set_audit_context=lambda *a: None,
          mark_inactive=lambda e, *a: setattr(e, 'activo', False),
          commit_or_conflict=lambda *a: None)
load_function('backend/app/services/documents.py', 'delete_document')
ns['delete_document'](DB(), 1, 'Motivo sintético', types.SimpleNamespace(id_usuario=99))
assert not links[1].activo
```

Sólo prueba control de flujo en Python. No incorpora triggers, transacciones ni política institucional: SS-05 sigue siendo Potencial. Su aceptación requiere acordar si el documento/versión es un activo global compartido y quién puede darlo de baja.

## Inventario de escenarios Python solicitados

Presencia comprobada por `git ls-files`; todos los siguientes están en el commit. Cada fila identifica fuente y función, no una aprobación actual. Dependencia común: conftest PostgreSQL; GDAL/archivos para GIS/importaciones; las suites no son seguras de ejecutar aquí sin ambiente desechable. En archivos con parametrización, una función representa varios escenarios.

| Archivo / función | Línea | Escenario indicado por la prueba | Ejecutada aquí |
|---|---:|---|---|
| `test_auth_rbac.py` / `test_auth_health_and_csrf` | 26 | auth health and csrf | No, sólo fuente |
| `test_auth_rbac.py` / `test_project_rbac_filters_before_pagination` | 37 | project rbac filters before pagination | No, sólo fuente |
| `test_credential_management.py` / `test_existing_user_login_with_password_over_72_utf8_bytes_is_generic_401` | 45 | existing user login with password over 72 utf8 bytes is generic 401 | No, sólo fuente |
| `test_credential_management.py` / `test_unknown_user_login_with_password_over_72_utf8_bytes_is_generic_401` | 56 | unknown user login with password over 72 utf8 bytes is generic 401 | No, sólo fuente |
| `test_credential_management.py` / `test_user_create_password_policy` | 76 | user create password policy | No, sólo fuente |
| `test_credential_management.py` / `test_password_policy_applies_to_own_change_and_admin_reset` | 90 | password policy applies to own change and admin reset | No, sólo fuente |
| `test_credential_management.py` / `test_current_password_over_72_utf8_bytes_is_422` | 104 | current password over 72 utf8 bytes is 422 | No, sólo fuente |
| `test_credential_management.py` / `test_password_hash_update_requires_actor_and_creates_no_empty_audit` | 114 | password hash update requires actor and creates no empty audit | No, sólo fuente |
| `test_credential_management.py` / `test_admin_changes_email_atomically_and_keeps_account_state` | 140 | admin changes email atomically and keeps account state | No, sólo fuente |
| `test_credential_management.py` / `test_email_permissions_and_inactive_target` | 171 | email permissions and inactive target | No, sólo fuente |
| `test_credential_management.py` / `test_own_password_change_revokes_sessions_without_empty_audit` | 184 | own password change revokes sessions without empty audit | No, sólo fuente |
| `test_credential_management.py` / `test_admin_password_reset_keeps_inactive_blocked_and_rejects_self` | 208 | admin password reset keeps inactive blocked and rejects self | No, sólo fuente |
| `test_person_project_access.py` / `test_person_scope_follows_every_actual_relationship_and_revocation` | 88 | person scope follows every actual relationship and revocation | No, sólo fuente |
| `test_person_project_access.py` / `test_shared_person_requires_all_projects_for_global_edit_and_preserves_read_scope` | 122 | shared person requires all projects for global edit and preserves read scope | No, sólo fuente |
| `test_person_project_access.py` / `test_other_authorized_project_cannot_link_an_out_of_scope_person` | 158 | other authorized project cannot link an out of scope person | No, sólo fuente |
| `test_person_project_access.py` / `test_orphan_person_creator_policy_and_first_link_without_implicit_project` | 188 | orphan person creator policy and first link without implicit project | No, sólo fuente |
| `test_person_project_access.py` / `test_service_update_entity_cannot_bypass_person_authorization` | 228 | service update entity cannot bypass person authorization | No, sólo fuente |
| `test_person_project_access.py` / `test_shared_person_edit_rechecks_scope_after_concurrent_link_commits` | 245 | shared person edit rechecks scope after concurrent link commits | No, sólo fuente |
| `test_person_project_access.py` / `test_inactive_project_reference_does_not_allow_shared_edit_or_creator_fallback` | 281 | inactive project reference does not allow shared edit or creator fallback | No, sólo fuente |
| `test_person_project_access.py` / `test_admin_invalid_person_reference_preserves_existing_conflict_contract` | 309 | admin invalid person reference preserves existing conflict contract | No, sólo fuente |
| `test_person_project_access.py` / `test_reference_patch_cannot_import_an_out_of_scope_person` | 322 | reference patch cannot import an out of scope person | No, sólo fuente |
| `test_person_project_access.py` / `test_bulk_agreement_creation_rejects_hidden_person_without_partial_rows` | 352 | bulk agreement creation rejects hidden person without partial rows | No, sólo fuente |
| `test_gis_management_rbac.py` / `test_inventory_covers_all_administrative_routes` | 99 | inventory covers all administrative routes | No, sólo fuente |
| `test_gis_management_rbac.py` / `test_only_operators_can_receive_new_project_assignments` | 109 | only operators can receive new project assignments | No, sólo fuente |
| `test_gis_management_rbac.py` / `test_anonymous_cannot_read_or_write_management` | 117 | anonymous cannot read or write management | No, sólo fuente |
| `test_gis_management_rbac.py` / `test_non_gis_sessions_cannot_access_any_management_route` | 129 | non gis sessions cannot access any management route | No, sólo fuente |
| `test_gis_management_rbac.py` / `test_gis_sessions_read_lists_details_geometries_and_revisions` | 141 | gis sessions read lists details geometries and revisions | No, sólo fuente |
| `test_gis_management_rbac.py` / `test_gis_session_can_record_revision_decision` | 152 | gis session can record revision decision | No, sólo fuente |
| `test_gis_management_rbac.py` / `test_published_map_and_indicators_keep_project_read_scope` | 162 | published map and indicators keep project read scope | No, sólo fuente |
| `test_gis_management_rbac.py` / `test_inactive_project_blocks_management_and_public_map` | 173 | inactive project blocks management and public map | No, sólo fuente |
| `test_gis_management_rbac.py` / `test_assignment_revocation_only_removes_operator_map_access` | 194 | assignment revocation only removes operator map access | No, sólo fuente |
| `test_gis_management_rbac.py` / `test_direct_missing_or_foreign_identifiers_preserve_not_found` | 209 | direct missing or foreign identifiers preserve not found | No, sólo fuente |
| `test_gis_management_rbac.py` / `test_withdrawn_import_keeps_private_history_and_never_revives_published_geometry` | 226 | withdrawn import keeps private history and never revives published geometry | No, sólo fuente |
| `test_gis_management_rbac.py` / `test_database_also_enforces_gis_roles_without_geographer_assignments` | 249 | database also enforces gis roles without geographer assignments | No, sólo fuente |
| `test_gis_management_rbac.py` / `test_database_still_rejects_forged_actor_and_inactive_project` | 262 | database still rejects forged actor and inactive project | No, sólo fuente |
| `test_gis_management_rbac.py` / `test_inactive_gis_user_cannot_reuse_session` | 282 | inactive gis user cannot reuse session | No, sólo fuente |
| `test_geospatial_imports.py` / `test_parcel_import_preview_confirmation_and_idempotency` | 31 | parcel import preview confirmation and idempotency | No, sólo fuente |
| `test_geospatial_imports.py` / `test_import_requires_explicit_target_mapping` | 88 | import requires explicit target mapping | No, sólo fuente |
| `test_geospatial_imports.py` / `test_legacy_trace_pipeline_and_map_remain_compatible` | 111 | legacy trace pipeline and map remain compatible | No, sólo fuente |
| `test_gis_concurrency_026.py` / `test_concurrent_reconciliation_numbers_and_request_dedup` | 85 | concurrent reconciliation numbers and request dedup | No, sólo fuente |
| `test_gis_concurrency_026.py` / `test_concurrent_same_confirmation_is_idempotent` | 99 | concurrent same confirmation is idempotent | No, sólo fuente |
| `test_gis_concurrency_026.py` / `test_two_deliveries_same_destination_keep_one_current_version` | 114 | two deliveries same destination keep one current version | No, sólo fuente |
| `test_gis_concurrency_026.py` / `test_concurrent_revision_generation_and_decisions_deduplicate` | 130 | concurrent revision generation and decisions deduplicate | No, sólo fuente |
| `test_document_targets_039.py` / `test_target_parcela_titular` | 265 | target parcela titular | No, sólo fuente |
| `test_document_targets_039.py` / `test_target_unidad_agraria` | 269 | target unidad agraria | No, sólo fuente |
| `test_document_targets_039.py` / `test_target_unidad_agraria_titular` | 273 | target unidad agraria titular | No, sólo fuente |
| `test_document_targets_039.py` / `test_target_afectacion_unidad_agraria` | 277 | target afectacion unidad agraria | No, sólo fuente |
| `test_document_targets_039.py` / `test_target_asamblea_convocatoria` | 281 | target asamblea convocatoria | No, sólo fuente |
| `test_document_targets_039.py` / `test_target_convenio_compareciente` | 285 | target convenio compareciente | No, sólo fuente |
| `test_document_targets_039.py` / `test_target_tramite_ran_pn` | 289 | target tramite ran pn | No, sólo fuente |
| `test_document_targets_039.py` / `test_target_tramite_ran_orv` | 293 | target tramite ran orv | No, sólo fuente |
| `test_document_targets_039.py` / `test_target_tramite_ran_evento_pn` | 297 | target tramite ran evento pn | No, sólo fuente |
| `test_document_targets_039.py` / `test_target_tramite_ran_evento_orv` | 301 | target tramite ran evento orv | No, sólo fuente |
| `test_document_targets_039.py` / `test_target_tramite_fifonafe_evento` | 305 | target tramite fifonafe evento | No, sólo fuente |
| `test_document_targets_039.py` / `test_target_expediente_requisito` | 309 | target expediente requisito | No, sólo fuente |
| `test_document_targets_039.py` / `test_target_404_not_found` | 313 | target 404 not found | No, sólo fuente |
| `test_document_targets_039.py` / `test_target_422_invalid_type` | 330 | target 422 invalid type | No, sólo fuente |
| `test_document_targets_039.py` / `test_target_403_unauthorized_project` | 340 | target 403 unauthorized project | No, sólo fuente |
| `test_document_targets_039.py` / `test_target_activity_authorized_round_trip` | 387 | target activity authorized round trip | No, sólo fuente |
| `test_document_targets_039.py` / `test_target_activity_unauthorized` | 411 | target activity unauthorized | No, sólo fuente |
| `test_document_targets_039.py` / `test_target_activity_read_roles` | 418 | target activity read roles | No, sólo fuente |
| `test_document_targets_039.py` / `test_target_activity_missing` | 438 | target activity missing | No, sólo fuente |
| `test_document_targets_039.py` / `test_target_activity_inactive` | 443 | target activity inactive | No, sólo fuente |
| `test_document_targets_039.py` / `test_target_activity_existing_link_and_versions` | 460 | target activity existing link and versions | No, sólo fuente |
| `test_document_targets_039.py` / `test_target_activity_requirement_unchanged` | 479 | target activity requirement unchanged | No, sólo fuente |
| `test_audit_api.py` / `test_changes_require_admin_and_return_sanitized_differences` | 63 | changes require admin and return sanitized differences | No, sólo fuente |
| `test_audit_api.py` / `test_change_filters_pagination_and_reactivation` | 97 | change filters pagination and reactivation | No, sólo fuente |
| `test_audit_api.py` / `test_access_events_and_append_only_privileges` | 120 | access events and append only privileges | No, sólo fuente |
| `test_audit_api.py` / `test_authenticated_requests_update_activity_without_audit_noise` | 162 | authenticated requests update activity without audit noise | No, sólo fuente |
| `test_audit_api.py` / `test_activity_update_requires_actor` | 183 | activity update requires actor | No, sólo fuente |
| `test_audit_api.py` / `test_activity_with_simultaneous_changes_is_audited_and_redacted` | 199 | activity with simultaneous changes is audited and redacted | No, sólo fuente |
| `test_audit_api.py` / `test_expiration_keeps_correlated_system_event_without_session_audit` | 226 | expiration keeps correlated system event without session audit | No, sólo fuente |
| `test_audit_api.py` / `test_logout_keeps_session_audit_and_access_event` | 247 | logout keeps session audit and access event | No, sólo fuente |
| `test_audit_api.py` / `test_system_expiration_validation_cannot_bypass_audit` | 263 | system expiration validation cannot bypass audit | No, sólo fuente |

## Contratos de DB y scripts relacionados

Ninguno ejecutado. Todos deben inspeccionarse de nuevo antes de ejecutarse en una fase autorizada: usar una conexión de prueba y respetar cada fixture. No copiarlos al checklist de comandos de sólo lectura de producción.

| Fuente versionada | Cobertura declarada | Dependencia / motivo de omisión |
|---|---|---|
| `backend/db/tests/001_baseline_v1_contract.sql` | Integridad de dominio/reporting/catálogo según migración del nombre | PostgreSQL; contiene o puede ejecutar escrituras/DDL/fixtures; omitido |
| `backend/db/tests/001_runtime_privileges.sh` | Privilegios owner/runtime, DML/DDL denegado y ledger | PostgreSQL; contiene o puede ejecutar escrituras/DDL/fixtures; omitido |
| `backend/db/tests/001_runtime_privileges.sql` | Privilegios owner/runtime, DML/DDL denegado y ledger | PostgreSQL; contiene o puede ejecutar escrituras/DDL/fixtures; omitido |
| `backend/db/tests/002_cierre_fuentes_excel_contract.sql` | Integridad de dominio/reporting/catálogo según migración del nombre | PostgreSQL; contiene o puede ejecutar escrituras/DDL/fixtures; omitido |
| `backend/db/tests/003_reporting_fuentes_excel_contract.sql` | Integridad de dominio/reporting/catálogo según migración del nombre | PostgreSQL; contiene o puede ejecutar escrituras/DDL/fixtures; omitido |
| `backend/db/tests/004_seguimiento_funcional_excel_contract.sql` | Integridad de dominio/reporting/catálogo según migración del nombre | PostgreSQL; contiene o puede ejecutar escrituras/DDL/fixtures; omitido |
| `backend/db/tests/005_reporting_cierre_excel_contract.sql` | Integridad de dominio/reporting/catálogo según migración del nombre | PostgreSQL; contiene o puede ejecutar escrituras/DDL/fixtures; omitido |
| `backend/db/tests/006_ajustes_reporting_post_auditoria_contract.sql` | Integridad de dominio/reporting/catálogo según migración del nombre | PostgreSQL; contiene o puede ejecutar escrituras/DDL/fixtures; omitido |
| `backend/db/tests/007_convenios_impactos_precision_contract.sql` | Integridad de dominio/reporting/catálogo según migración del nombre | PostgreSQL; contiene o puede ejecutar escrituras/DDL/fixtures; omitido |
| `backend/db/tests/007_convenios_impactos_regression.sql` | Integridad de dominio/reporting/catálogo según migración del nombre | PostgreSQL; contiene o puede ejecutar escrituras/DDL/fixtures; omitido |
| `backend/db/tests/008_fifonafe_evolucion_contract.sql` | Integridad de dominio/reporting/catálogo según migración del nombre | PostgreSQL; contiene o puede ejecutar escrituras/DDL/fixtures; omitido |
| `backend/db/tests/008_fifonafe_evolucion_regression.sql` | Integridad de dominio/reporting/catálogo según migración del nombre | PostgreSQL; contiene o puede ejecutar escrituras/DDL/fixtures; omitido |
| `backend/db/tests/019_catalogo_nucleos_ran_contract.sql` | Integridad de dominio/reporting/catálogo según migración del nombre | PostgreSQL; contiene o puede ejecutar escrituras/DDL/fixtures; omitido |
| `backend/db/tests/021_derecho_via_proyecto_contract.sql` | Historia, linaje y geometrías/conciliación | PostgreSQL; contiene o puede ejecutar escrituras/DDL/fixtures; omitido |
| `backend/db/tests/022_importacion_ddv_gpkg_contract.sql` | Historia, linaje y geometrías/conciliación | PostgreSQL; contiene o puede ejecutar escrituras/DDL/fixtures; omitido |
| `backend/db/tests/025_conciliacion_gis_proyecto_contract.sql` | Historia, linaje y geometrías/conciliación | PostgreSQL; contiene o puede ejecutar escrituras/DDL/fixtures; omitido |
| `backend/db/tests/026_historia_cambios_gis_contract.sql` | Historia, linaje y geometrías/conciliación | PostgreSQL; contiene o puede ejecutar escrituras/DDL/fixtures; omitido |
| `backend/db/tests/027_actividad_campo_objetivo_documental_contract.sql` | Integridad de dominio/reporting/catálogo según migración del nombre | PostgreSQL; contiene o puede ejecutar escrituras/DDL/fixtures; omitido |
| `backend/db/tests/028_catalogo_tipo_documento_contract.sql` | Integridad de dominio/reporting/catálogo según migración del nombre | PostgreSQL; contiene o puede ejecutar escrituras/DDL/fixtures; omitido |
| `backend/db/tests/029_diagnosticos_conciliacion_gis_contract.sql` | Historia, linaje y geometrías/conciliación | PostgreSQL; contiene o puede ejecutar escrituras/DDL/fixtures; omitido |

`backend/scripts/run_migrations.sh`, `db/init/*`, scripts de creación/desbloqueo, tests de upgrade/lineage y benchmarks **no se ejecutaron**. Crear o cerrar una sesión también escribe auditoría, aunque una prueba se anuncie como de consulta. `qa_roles_readonly.py` establece READ ONLY pero conecta a DB y lee entidades reales; se omitió por el alcance de esta fase.

## Plan de pruebas faltantes, sin ejecutarlo

1. En clon desechable y datos sintéticos, parametrizar todas las filas de MATRIZ-ENDPOINTS-RBAC.md, con dos proyectos y relaciones compartidas. Mantener positivos y negativos; no limitarse a ocultar botones.
2. Añadir regresión de XSS del trayecto de parcela/mapa y contexto atributo/texto, tooltips y exportación. Verificar CSP/headers finales mediante navegador.
3. Corpus GIS sintético acotado: ZIP con rutas y symlinks, muchos elementos pequeños, geometría compleja, múltiples capas, salida sin newline, timeouts, cancelación y crash. Worker sin secretos/red; no usar archivos desconocidos para validar un parser sin aislamiento.
4. Login con IP real de proxy, ventanas globales/cuenta, estado bloqueado y concurrencia; revocación/cambio de contraseña mientras hay lectura/escritura en curso. Medir expiración sin solicitudes que renueven actividad.
5. Documento multivínculo A/B, versiones antiguas, MIME/firma falsos, contenido activo benigno, cargas concurrentes y fallos de commit; restauración coordinada DB+volumen y limpieza segura.
6. Runtime/owner/TEMP/search_path en DB desechable, actores falsos, append-only y DDL; SCA completo con versiones/digests reales y secret scanning con redacción, incluyendo clasificación de capturas/fixtures.
7. Disponibilidad: acordar dataset y objetivos de memoria/tiempo/concurrencia; comenzar con casos límite de una solicitud, luego pruebas acotadas autorizadas. No realizar estrés contra producción.

**Conclusión de cobertura:** buena base de regresión funcional y permisos; evidencia actual aislada limitada. No hay cobertura suficiente demostrada de los controles críticos de contenido hostil, aislamiento, cuotas ni despliegue efectivo para declarar preparación institucional.
