# Estabilización excepcional del linaje GIS — 2026-10-05

> **Alcance histórico (aclaración documental, 2026-10-08):** Informe histórico del corte de estabilización 001–025. Las versiones, checksums, conteos y pruebas siguientes documentan aquella ejecución; el inventario canónico actual llega a 028 e incluye la historia GIS de 026. Véase [MIGRACIONES.md](MIGRACIONES.md). No se actualizan retrospectivamente sus resultados.

**CADENA 001–025 ESTABILIZADA.** Todos los criterios A–M cumplidos. Sin commit ni push.

## 1. HEAD inicial/final

`a829f1c631e4ee56c0ce26edcb3615ceaf5d61f8` en ambos casos. Sin commit, push, merge, rebase ni reset.

## 2. Remoto utilizado

`origin/feature/backend-logica` = `49f12f747a1eda4fc75930d78e0f23dd00baf422`, comprobado mediante fetch antes de editar. Ancestro común `cf07d7ea519794ee558229de88681c05e9e0fa01`; 5 commits GIS y 2 remotos exclusivos.

## 3–4. Renumeración y SHA antiguo → canónico

Sólo metadatos de versión en SQL; cuerpos funcionales idénticos byte por byte.

| Archivo antiguo | Archivo canónico | SHA antiguo | SHA canónico |
|---|---|---|---|

| 020_derecho_via_proyecto.sql | 021_derecho_via_proyecto.sql | `3662cc9ce0ed2e63095b7a873616356aa965e94b1b34e9f651ffd5396452dc09` | `c759eaab96a7ed88679fd5fa288504b4bdf36724479d82e155044a572da90d4e` |

| 021_importacion_ddv_gpkg.sql | 022_importacion_ddv_gpkg.sql | `16f63229569574f078105423a1a914c1621b6662150dfc090124f60817b719f6` | `40e988e06f7f211995ea62456ee7fc64e951fabd2ff14609f155de968171d58f` |

| 022_importacion_nucleos_gpkg.sql | 023_importacion_nucleos_gpkg.sql | `a244ed434176feff02ceacbb0e5204bebe0bb16d582dbb4efdea9a13a41ebf0b` | `ede1ea43947cec0f9f9ba433319d69de21847c892985adbd03feed80ef0f051b` |

| 023_importacion_parcelas_gpkg.sql | 024_importacion_parcelas_gpkg.sql | `6491328bf6da3f22af31e1ae93e4569ba3836493043748d40cbc23fe26d3a7dd` | `15f36ea78a591aeb0f587a84e7e2bddb21f53de455d80daaf8532422796bc2d6` |

| 024_conciliacion_gis_proyecto.sql | 025_conciliacion_gis_proyecto.sql | `c1a6684b06682ba63a9ad090c561d1cf2b9fee5b0fc1ce0da7f6c0a7952399c4` | `8338aace95845761acf0f9b675064ca25a6b0da2117013178ed060f260ec372a` |


## 5. Heartbeat

`020_auditoria_heartbeat_sesion.sql`: `cfa4dadb2e8b5bb9b8cddddf617c34132380ad49a660de9037de43850263f4c8`. Bytes idénticos al remoto.

## 6–7. Dependencias y advisory locks

020 heartbeat exige019 común; 021 DDV exige020 heartbeat; 022 importación DDV exige021 DDV; 023 núcleos exige022 importación DDV; 024 parcelas exige023 núcleos; 025 conciliación exige024 parcelas. Cada guardia exige el SHA exacto de su predecesor.

```text
software-pa:021:derecho-via-proyecto
software-pa:022:importacion-ddv-gpkg
software-pa:023:importacion-nucleos-gpkg
software-pa:024:importacion-parcelas-gpkg
software-pa:025:conciliacion-gis-proyecto
```

## 8–9. Manifiestos

[gis_lineage_manifest.json](../backend/db/lineage/gis_lineage_manifest.json) congela 001–019 comunes, antiguos GIS020–024 y canónicos020–025. Los originales se archivan en `backend/db/lineage/gis_precanonical/`, fuera del runner. El antiguo024 estaba sin commit; su archivo y SHA conservan también ese trabajo local.

[gis_legacy_schema_signature.json](../backend/db/lineage/gis_legacy_schema_signature.json) congela firmas estructurales. Ambos SHA están fijados en el reconciliador. No contienen datos personales ni credenciales.

## 10. Dry-run

PASS en `software_pa_test`: linaje exacto, firma estructural exacta, 24 filas, modo de sólo lectura y cero UPDATE. Evidencia local: `backups/lineage_gis_20261005/dry-run.json`.

## 11–14. Ledger y runner

Antes: exactamente 001–024, 020 DDV. Después del reconciliador: 001–019 + 021–025, 24 filas y 020 ausente. Runner: aplicó únicamente 020 heartbeat y verificó por SHA las GIS, sin repetir DDL. Final: exactamente 001–025, todos los nombres/checksums iguales al manifiesto.

| Versión canónica | Nombre | aplicada_en UTC |
|---|---|---|

| 001 | baseline_v1 | 2026-09-04 16:47:04.734971+00:00 |

| 002 | cierre_fuentes_excel | 2026-09-04 16:47:22.684169+00:00 |

| 003 | reporting_fuentes_excel | 2026-09-07 17:47:19.947771+00:00 |

| 004 | seguimiento_funcional_excel | 2026-09-07 17:47:20.041603+00:00 |

| 005 | reporting_cierre_excel | 2026-09-07 17:47:20.145746+00:00 |

| 006 | ajustes_reporting_post_auditoria | 2026-09-07 17:47:20.252660+00:00 |

| 007 | convenios_impactos_precision | 2026-09-07 23:53:28.640387+00:00 |

| 008 | fifonafe_evolucion_forward_only | 2026-09-08 15:55:51.464399+00:00 |

| 009 | bitacora_append_only | 2026-09-10 19:11:48.364471+00:00 |

| 010 | credenciales_auditoria | 2026-09-10 20:01:43.433093+00:00 |

| 011 | auditoria_actor_update | 2026-09-10 22:24:58.870359+00:00 |

| 012 | correccion_snapshot_tuc_triestado | 2026-09-15 17:31:04.446069+00:00 |

| 013 | pagos_en_reporting | 2026-09-15 17:31:04.541583+00:00 |

| 014 | convenios_colectivos_por_destino | 2026-09-15 17:31:04.627209+00:00 |

| 015 | exclusion_proyectos_inactivos | 2026-09-15 17:31:04.712430+00:00 |

| 016 | normalizacion_convenio_superficie_adicional | 2026-09-15 17:58:01.021209+00:00 |

| 017 | normalizar_contexto_asamblea_adicional | 2026-09-15 20:15:14.923705+00:00 |

| 018 | orv_persona_ciclo_vida | 2026-09-17 18:07:07.955570+00:00 |

| 019 | catalogo_nucleos_ran | 2026-09-21 23:28:53.213294+00:00 |

| 020 | auditoria_heartbeat_sesion | 2026-10-05 21:10:53.286300+00:00 |

| 021 | derecho_via_proyecto | 2026-09-25 22:05:24.750190+00:00 |

| 022 | importacion_ddv_gpkg | 2026-09-25 22:35:49.564945+00:00 |

| 023 | importacion_nucleos_gpkg | 2026-09-25 22:58:33.464728+00:00 |

| 024 | importacion_parcelas_gpkg | 2026-09-28 17:51:06.715513+00:00 |

| 025 | conciliacion_gis_proyecto | 2026-10-05 18:05:33.806392+00:00 |


Todas las fechas GIS originales se conservaron al desplazar las versiones; heartbeat020 tiene fecha posterior a GIS021–025, como corresponde. Dumps JSON del ledger y reportes before/apply/after/runner quedan en la evidencia local ignorada por Git.

## 15. Validación heartbeat

21 pruebas de auditoría pasaron: actor obligatorio, heartbeat sin ruido, cambios simultáneos incluidos secretos auditados/redactados, expiración correlacionada y rechazo de intentos de bypass. La definición final también coincide con la instalación limpia.

## 16. Integración remota

Integración manual sin operaciones de rama. Todos los archivos remotos exclusivos incorporados conservan sus bytes: routers/domain/users, services/access/domain, conftest, observadores de concurrencia, pruebas de personas/asignaciones/auditoría y documentación API/QA/openapi. `test_auth_rbac.py` conserva las pruebas y actualiza el esquema esperado a25. MIGRACIONES integra ambos linajes. Restricciones y pruebas GIS locales preservadas.

## 17. Contrato 001

Se exige el conjunto completo de tablas baseline y columnas esenciales, constraints y funciones/vistas que sobreviven. Se elimina el conteo global51. Se verifican dependencias transitivas reales de reporting, compatible con las capas introducidas desde005. SQL001 intacto.

## 18. Contrato 008

Se compara el mismo universo legado con proyectos activos cuando015 está aplicada. Se conservan backfill, evidencia, ACL y aserciones de cardinalidad; reporting productivo y SQL008 intactos. La regresión SQL007 también adapta únicamente su fixture a `id_tipo_fin` exigido por018, preservando fechas y aserciones originales y compatibilidad pre018.

## 19. Equivalencia A/B

PASS. A instalación limpia canónica; B antiguo→reconciliador→runner. Comparación exacta de columnas, constraints, ACL/default ACL, extensiones, funciones, índices, políticas, relaciones/vistas/owners, secuencias, triggers y tipos. Metadata GIS desde catálogos/typmod/checks; sin reparar geometry_columns. Ledger lógico idéntico (fechas verificadas por preservación, no igualdad entre instalaciones). El esquema final persistente también es idéntico al de A.

Instancia aislada tmpfs, sin puertos ni volúmenes permanentes, única DB `software_pa_test`; eliminada al terminar. Los tests de ledger comprueban además `cluster_name=software-pa-lineage-equivalence` antes de cualquier escritura. Reproducción: `backend/scripts/test_gis_lineage_equivalence.py`, con las tres guardas de test.

## 20. Preservación de datos

Los hashes de todas las filas y conteos coincidieron antes del reconciliador, después y tras el runner. Geometrías incluidas como EWKB NDR antes de calcular firmas. Cero filas administrativas/GIS cambiadas por reconciliador/runner. Las pruebas funcionales posteriores usan fixtures sintéticos por sus flujos normales; la comparación de preservación se realizó antes de esas pruebas.

| Tabla | Conteo conservado |
|---|---:|

| afectacion | 4465 |

| convenio | 1765 |

| derecho_via_proyecto | 12 |

| importacion_archivo | 69 |

| importacion_feature | 104 |

| importacion_feature_candidato | 25 |

| importacion_feature_decision | 15 |

| nucleo_agrario | 37205 |

| parcela | 1507 |

| proyecto | 4802 |

| proyecto_configuracion_gis | 0 |

| proyecto_nucleo | 4894 |

| proyecto_nucleo_geometria | 5 |

| proyecto_parcela_geometria | 10 |

| seguimiento_evento | 2394 |

| tramite_ran | 1634 |

| tramite_ran_evento | 3319 |


## 21. SQL

12 contratos y2 regresiones SQL:14 passed,0 failed. Contrato runtime/ACL adicional:PASS. 001/008 y todas las migraciones comunes conservan sus SHA.

## 22. Tests dirigidos

38 pruebas del reconciliador:38 passed,0 failed,1 warning en instancia aislada. Rechazos de entorno/base/ledger/SHA/estructuras; sólo lectura; fechas; cinco pasos y rollback; advisory/table lock; commit incierto; reejecución pendiente/canónica.

Regresiones dirigidas:89 passed,17 skipped,1 warning; los skips son las pruebas de escritura del ledger reservadas a la instancia aislada. Una primera invocación sin credenciales TEST_ADMIN falló en setup; se corrigió el entorno con credenciales sintéticas, sin modificar autenticación.

## 23. Suite completa

**495 passed, 0 failed, 0 errors, 24 skipped, 1 warning; 733.46 segundos.** 519 casos recolectados. Incluye GIS, CRS, precisión, candidatos/decisiones, historial, RAN, reporting, mapa existente y endpoints legacy. Los skips son23 tests exclusivos del servidor desechable (todos pasados allí) y el test que exige un único admin activo. Warning previo de Starlette/httpx. JUnit guardado localmente. El ledger se volvió a verificar tras la suite: mismo manifiesto y mismas fechas.

## 24. git diff --check

`git diff --check`: exit0, sin salida. Sin errores de whitespace en archivos nuevos de esta fase. Un informe preexistente sin seguimiento conserva su aviso de línea final vacía; no se editó ese trabajo previo.

## 25. Git

Sin cambios staged. HEAD intacto. Las eliminaciones y archivos nuevos corresponden a renumeraciones, cuyo reconocimiento como rename no requiere ni justifica hacer git add/commit. Estado final:

```text
 M backend/app/models.py
 M backend/app/routers/domain.py
 M backend/app/routers/geospatial_imports.py
 M backend/app/routers/users.py
 M backend/app/schemas.py
 M backend/app/services/access.py
 M backend/app/services/domain.py
 M backend/app/services/geospatial_imports.py
 M backend/app/services/gis_ingestion.py
 D backend/db/migrations/020_derecho_via_proyecto.sql
 D backend/db/migrations/021_importacion_ddv_gpkg.sql
 D backend/db/migrations/022_importacion_nucleos_gpkg.sql
 D backend/db/migrations/023_importacion_parcelas_gpkg.sql
 M backend/db/tests/001_baseline_v1_contract.sql
 M backend/db/tests/007_convenios_impactos_regression.sql
 M backend/db/tests/008_fifonafe_evolucion_contract.sql
 D backend/db/tests/020_derecho_via_proyecto_contract.sql
 D backend/db/tests/021_importacion_ddv_gpkg_contract.sql
 M backend/tests/conftest.py
 M backend/tests/test_audit_api.py
 M backend/tests/test_auth_rbac.py
 M backend/tests/test_geospatial_imports.py
 M backend/tests/test_nucleus_gpkg_imports.py
 M backend/tests/test_parcel_gpkg_imports.py
 D backend/tests/test_schema_020_derecho_via_proyecto.py
 M docs/API.md
 M docs/ARQUITECTURA.md
 M docs/DICCIONARIO_DATOS.md
 M docs/MIGRACIONES.md
 M docs/openapi.json
?? backend/app/services/gis_attributes.py
?? backend/app/services/gis_reconciliation.py
?? backend/db/lineage/
?? backend/db/migrations/020_auditoria_heartbeat_sesion.sql
?? backend/db/migrations/021_derecho_via_proyecto.sql
?? backend/db/migrations/022_importacion_ddv_gpkg.sql
?? backend/db/migrations/023_importacion_nucleos_gpkg.sql
?? backend/db/migrations/024_importacion_parcelas_gpkg.sql
?? backend/db/migrations/025_conciliacion_gis_proyecto.sql
?? backend/db/tests/021_derecho_via_proyecto_contract.sql
?? backend/db/tests/022_importacion_ddv_gpkg_contract.sql
?? backend/db/tests/025_conciliacion_gis_proyecto_contract.sql
?? backend/scripts/lineage_inspection.py
?? backend/scripts/reconcile_gis_migration_lineage.py
?? backend/scripts/test_gis_lineage_equivalence.py
?? backend/tests/concurrency.py
?? backend/tests/lineage_compose.yml
?? backend/tests/test_assignment_concurrency_regressions.py
?? backend/tests/test_gis_confirmation_024.py
?? backend/tests/test_gis_history_regressions.py
?? backend/tests/test_gis_preflight_024.py
?? backend/tests/test_migration_lineage.py
?? backend/tests/test_person_project_access.py
?? backend/tests/test_project_user_assignments.py
?? backend/tests/test_schema_021_derecho_via_proyecto.py
?? docs/DERECHOS_COLECTIVOS_PARA_FRONTEND.md
?? docs/INFORME_AUDITORIA_HISTORIA_GIS_2026-10-05.md
?? docs/INFORME_CONCILIACION_GIS_2026-10-05.md
?? docs/INFORME_DERECHOS_COLECTIVOS_2026-10-02.md
?? docs/INFORME_ESTABILIZACION_LINAJE_GIS_2026-10-05.md
?? docs/QA_ASIGNACIONES_PROYECTO.md
?? docs/QA_AUDITORIA_HEARTBEAT_020.md
```

`git diff --stat`:

```text
 backend/app/models.py                              |  68 ++
 backend/app/routers/domain.py                      |  23 +-
 backend/app/routers/geospatial_imports.py          |  58 +-
 backend/app/routers/users.py                       |   6 +-
 backend/app/schemas.py                             |  51 ++
 backend/app/services/access.py                     | 105 ++-
 backend/app/services/domain.py                     | 108 ++-
 backend/app/services/geospatial_imports.py         | 629 ++--------------
 backend/app/services/gis_ingestion.py              |  34 +-
 backend/db/migrations/020_derecho_via_proyecto.sql |  75 --
 backend/db/migrations/021_importacion_ddv_gpkg.sql |  95 ---
 .../db/migrations/022_importacion_nucleos_gpkg.sql | 106 ---
 .../migrations/023_importacion_parcelas_gpkg.sql   | 120 ----
 backend/db/tests/001_baseline_v1_contract.sql      |  99 ++-
 .../db/tests/007_convenios_impactos_regression.sql |  12 +-
 .../db/tests/008_fifonafe_evolucion_contract.sql   |  38 +-
 .../db/tests/020_derecho_via_proyecto_contract.sql | 206 ------
 .../db/tests/021_importacion_ddv_gpkg_contract.sql |  54 --
 backend/tests/conftest.py                          |   6 +
 backend/tests/test_audit_api.py                    | 162 ++++-
 backend/tests/test_auth_rbac.py                    |   2 +-
 backend/tests/test_geospatial_imports.py           |  31 +-
 backend/tests/test_nucleus_gpkg_imports.py         | 384 ++++------
 backend/tests/test_parcel_gpkg_imports.py          | 396 ++++------
 .../tests/test_schema_020_derecho_via_proyecto.py  |  32 -
 docs/API.md                                        |  74 +-
 docs/ARQUITECTURA.md                               |  49 +-
 docs/DICCIONARIO_DATOS.md                          |  56 +-
 docs/MIGRACIONES.md                                | 122 +++-
 docs/openapi.json                                  | 793 +++++++++++++++++----
 30 files changed, 1993 insertions(+), 2001 deletions(-)
```

## 26. Riesgos restantes

No existe026 ni se implementaron reconciliación tardía, revisiones GIS, transversales, frontend, cambios de mapa o lógica RAN/SeguimientoEvento. geometry_columns conserva su defecto previo, fuera de alcance. El reconciliador sólo acepta la instalación aprobada, no estados desconocidos. Debe mantenerse exclusión del runner durante cualquier adopción futura; no hay bloqueo global compartido con el runner ordinario. Warning existente de Starlette/httpx. La historia Git continúa divergente porque la integración fue manual y quedó sin commit; las intenciones remotas se preservaron y el workspace contiene la cadena canónica adoptada por la base. Las otras instalaciones requieren auditar su linaje antes de cualquier adopción; este script no acepta otro nombre de base.
