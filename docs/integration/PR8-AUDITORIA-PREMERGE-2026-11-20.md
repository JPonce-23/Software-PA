# PR #8 — Auditoría pre-merge sin GHCR

Fecha: 2026-11-20, America/Mexico_City. **Recomendación: NO MERGE por ahora.** La integración Git y los contratos offline aprueban; faltan la importación conservando identidad y las pruebas reales sobre instancia independiente desechable. GHCR no es una necesidad técnica de ese camino: puede sustituirse por el archivo congelado validado. No se concede una excepción ni se autoriza producción.

## 1. Alcance y procedencia

Worktree auditado: `/home/alfredo/proyectos/Software-PA-preflight-qa`, rama `security/integracion-pa5-final-20261118`. HEAD inicial exacto: `8dcaf74a84edfc5a47b7d1e2d54d081fdd70be72`. Estado inicial limpio. El repositorio original se consultó sin editarlo; sus cambios previos permanecen ajenos a esta auditoría.

Evidencia nueva: consultas SSH de lectura por el alias preexistente `patrenes` con BatchMode/StrictHostKeyChecking; metadatos GitHub mediante el conector; lectura del archivo original y validaciones locales reales. No se imprimieron credenciales ni se consultaron registros de aplicación. La consulta SQL exitosa forzó `default_transaction_read_only=on` y timeout de 5 s. Un primer intento como rol `postgres` falló porque ese rol no existe; se consultó después mediante el usuario ya configurado, sin mostrar su valor ni contraseñas. No se modificaron servicios, volúmenes o bases.

Evidencias reproducibles: `outputs/pr8-premerge-20261120/` en este worktree (ignorado por Git), especialmente `server-readonly.log`, `github-evidence.json`, `archive-report.json`, `layout-report.json`, `compose-results.json`, `offline-results.json` y `logs/`. El árbol OCI materializado permanece en `/tmp/pr8-premerge-20261120/oci`; no se incorpora al repositorio. Las evidencias históricas de etapas anteriores se distinguen de estas ejecuciones.

## 2. Servidor y diferencias de runtime

| Elemento | Observado mediante SSH | PR #8 / artefacto |
|---|---|---|
| Sistema | Ubuntu 24.04.5 LTS, kernel 6.8.0-149-generic, x86_64 | linux/amd64 |
| Engine / contexto | Docker 29.1.3 / `default`; almacén containerd | Exige almacén containerd |
| Engine ID protegido | `38a3bf79-1712-4ce7-a5d7-a23d15d6395a` | No autorizado para importación/pruebas |
| Compose | 2.40.3 | Producción requiere >= 2.24.4 por `!reset` |
| PostgreSQL efectivo | 15.4, paquete 15.4-1.pgdg110+1 | Paquete 15.19-1.pgdg13+2 |
| PostGIS efectivo | 3.3.4, confirmado por SQL | 3.6.4 |
| GDAL | Paquete instalado libgdal28 3.2.2+dfsg-2+deb11u2 | libgdal36 3.10.3+dfsg-1+pa5 |
| Commit desplegado | `929fa135436066c6d3618f181d7e86cbca97065a` | HEAD auditado indicado arriba |

El GDAL instalado del servidor no se presenta como versión efectiva del raster: no apareció `postgis_raster` entre las extensiones consultadas y `postgis_full_version()` no declaró GDAL. GEOS 3.9.0 y PROJ 7.2.1 sí se observaron en PostGIS. No se intentó instalar extensiones para ampliar evidencia.

Contenedores: frontend_ssalfer, backend, pgAdmin y DB ejecutándose; backend/pgAdmin/DB saludables. El frontend anterior está detenido. Compose desplegado reside en `/home/trenes/software-pa` y selecciona base + ssalfer. `docker-compose.ssalfer.yml` tiene una modificación local; no se leyó su contenido ni se sobrescribió. El commit desplegado es ancestro del PR, con 739 archivos distintos en Git; esto no equivale a una comparación de todos los archivos del servidor.

## 3. Comparación de imágenes e identidades OCI

| Imagen relevante en servidor | Digest / identidad observada | Comparación |
|---|---|---|
| `postgis/postgis:15-3.3` | `sha256:a2fc46b52819d25add4ed93d3da83e106e17ea3ace6883cce3791631c9820bb2` | DB activa; distinta de +pa5 |
| `postgis/postgis` sin tag | `sha256:91098df530c92202d69193ded45dd47e6d0b6a3117a6398b0abe2be365f23550` | Presente; no validada como +pa5 |
| `software-pa-backend:latest` | `sha256:6c1bda1c8d59d42303bd491f137e7d913449a056f96ca70d7d9288715833db93` | Identidad observada; no demuestra build del PR |
| `software-pa-frontend_ssalfer:latest` | `sha256:24cc4d99fbcc7f408ace34bb383f351870d45d78321c5ce725a652c362ae373e` | Identidad observada; no demuestra build del PR |
| pgAdmin fijado por Compose | `sha256:40fa840c5bb7c8463957f1255b01283732c2d8c9396a956d180f8e6c296753b3` | Disponible y utilizado |
| candidato +pa5 | No aparece en inventario del servidor | Referencia exacta no disponible allí |

El inventario completo de nueve imágenes está en `server-readonly.log`; no se deducen equivalencias por nombres de tags.

Archivo original: `pa5-validated-image.tar`, 263294464 bytes, SHA-256 **`4099c542cf891338320396fca45fac0bc47bd1064217e70b331259981ad025b2`**, recalculado y coincidente.

Identidades distintas verificadas a partir de bytes:

- **Index digest**: `sha256:d413671654deef3c43367ea3fd0be56a32a36d75b9d971970e33ec56a76b7c3c`. Selecciona manifest amd64 y attestation.
- **Manifest digest amd64**: `sha256:27e9ca0702414c9515cf205df5635af7ad7509385dffcf7dcf6fb048c185f9b7`. Referencia configuración y capas ordenadas.
- **Config digest**: `sha256:dfe80e1feb214799ba101b037f0b72e2499de606a63ef88497f4e13bb1ed3f19`. Identifica el JSON de configuración/rootfs; no es el índice.

`validar-pa5-oci.py` original aprobó. También aprobó el validador más estricto `pa5_supply.py layout` contra el catálogo: 33 blobs, 29 capas, descriptores/tamaños/hashes, diff IDs, manifest/config, plataforma, paquetes instalados en las capas y cinco payloads protegidos GDAL/core/bitcode LLVM. Se conservaron las attestations. Esto prueba contenido offline, no carga dinámica ni ejecución nativa.

**Investigación del supuesto error de identidad:** `verificar-pa5-engine.sh` NO interpreta el config digest como index digest. Exige containerd y compara `.Id` y `.Descriptor.digest` con el índice. La evidencia histórica registra precisamente ese Id para +pa5; una inspección real del servidor confirmó `.Id == Descriptor.digest` para su imagen almacenada como manifest. El código de Moby asigna `ID: target.Digest.String()` en este almacén ([implementación oficial](https://github.com/moby/moby/blob/master/daemon/containerd/image_inspect.go)). En el almacén clásico cambia la semántica; este script lo rechaza. No se sustituyó el hash esperado ni se amplió el conjunto de IDs aceptados. Se añadió un comentario y regresión de esta distinción. El consumidor remoto ya contempla explícitamente la variación de semántica entre almacenes.

## 4. Importación y smoke nativo

**BLOCKED.** Sólo se identificó el contexto local `default`; su socket denegó acceso dentro del sandbox. Ese contexto corresponde al proyecto y no se utilizó ni se escaló para ejecutar Docker. El servidor tampoco es desechable. No se identificó otro endpoint vacío con autorización explícita. Disponer de `dockerd` instalado no certifica una instancia aislada.

No hubo `docker image load`, create/run real, reconstrucción, pull, publicación ni smoke nativo +pa5. Las regresiones usan respuestas sintéticas y se detienen deliberadamente antes de crear un contenedor; no constituyen evidencia del Engine. Procedimiento de continuación preparado en `PR8-PROCEDIMIENTO-DESECHABLE-2026-11-20.md`.

## 5. Compatibilidad Compose

Tres renderizados reales mediante Compose 5.3.1 local, `--env-file /dev/null`, variables exclusivamente sintéticas y perfil admin-tools: base, base+override+ssalfer, base+ssalfer+prod. Todos aprobaron las referencias exactas, `linux/amd64` y `pull_policy: never`. En producción DB/backend/frontend/pgAdmin no publican puertos; sólo TLS publica 80/443. En desarrollo los puertos son loopback. No se arrancaron servicios.

El servidor cumple arquitectura, almacén y versión mínima de Compose; falta su imagen +pa5. Con `pull_policy: never`, no puede aprovisionarse automáticamente: **bloqueo de despliegue/portabilidad**, no conflicto Git. Resolverlo requiere distribución del archivo verificada en entorno autorizado, sin permitir fallback. Los renderizados no prueban certificados, builds, readiness ni capacidad. El backend utiliza su GDAL ABI39 separado del ABI36 de PostGIS.

`deploy/PA5-COMPOSE.md` conserva narrativa histórica que dice que falta integrar dev; el HEAD auditado ya lo integró. Sus advertencias sobre suministro, no arrancar bases y comprobar identidad siguen aplicando; la comparación Git nueva de esta auditoría prevalece sobre esa frase histórica.

## 6. Migraciones, roles y backend

**Pruebas reales sobre DB nueva: BLOCKED.** No se aplicó ninguna de las 34 migraciones ni se probaron roles/privilegios efectivos o API contra PostgreSQL +pa5. No se habilitaron fixtures de escritura contra el servidor.

Comprobaciones ejecutadas: gramática PostgreSQL de las 34 migraciones PASS mediante pglast; sin diferencias respecto al dev remoto; contratos offline del runner/roles dentro de las 631 pruebas PASS. `backend/tests/test_migration_lineage.py`: 15 PASS, 23 SKIPPED por ausencia de la instancia con marcador obligatorio. Esas 23 no cuentan como PASS. Primer intento de colección sin SECRET_KEY sintético rechazado; la invocación corregida es la conservada en el log final.

Riesgos revisados en código: bootstrap de roles requiere usuario runtime separado y precede a migraciones; baseline requiere `software_pa_app`; runner valida continuidad/checksums e impide aplicar sobre objetos existentes sin historial. Cada migración tiene su transacción, pero la campaña completa puede quedar parcialmente aplicada si falla una posterior. En un volumen existente el entrypoint no repite init; cambiar imagen no aplica automáticamente roles/migraciones ni actualización SQL de extensiones. No se verificó el ledger del servidor ni se asegura que acepte la migración canónica. No usar reconciliación histórica fuera de su inventario/marcador autorizado.

La suite backend completa, autenticación efectiva, privilegios reales, comportamiento de 034, GDAL backend, carga/actualización de extensiones y actualización de un volumen restaurado permanecen pendientes. La coincidencia del major 15 no demuestra que el despliegue sea seguro.

## 7. Comparación remota y cuatro checks

La API GitHub confirmó PR #8 abierto, draft, `mergeable=true`, HEAD `8dcaf74…` y base remota actual `dev=c1b4a00317c4915d0ae4a77e37de4c1b1af09f92`. Esa base es ancestro del HEAD: no hay conflicto pendiente con dev en la instantánea consultada. Diff del PR: 105 archivos, +26154/-1112. Se usó la base de la API, no el dev del repositorio original con trabajo local.

Checks remotos del HEAD original, consultados por job:

| Check | Estado |
|---|---|
| Python offline security | PASS |
| SSALFER Node regressions | PASS |
| SS-09 and configuration integrity | PASS |
| PA5 offline supply contracts | PASS |
| PA5 registry identity and native smoke | NOT RUN: skipped por PR draft |

Fuentes: [regresiones remotas](https://github.com/JPonce-23/Software-PA/actions/runs/44595500850), [suministro remoto](https://github.com/JPonce-23/Software-PA/actions/runs/44595501744), [PR #8](https://github.com/JPonce-23/Software-PA/pull/8). El éxito global del workflow no convierte su job omitido en aprobado. No se consultaron exhaustivamente reglas/protecciones administrativas de la rama.

Revalidación local tras la corrección: 33 suites/631 tests de seguridad PASS, Node 154 PASS, integridad SS-09 PASS, dos archivos SheetJS contra distribución oficial fijada PASS, shell PASS, `pip check` PASS. Los contratos PA5 aumentaron de 23 a 27 tests. Linaje offline suma otros 15 PASS/23 omitidos: **800 tests aprobados, 0 fallidos, 23 omitidos en la ejecución final**. La primera corrida restringida se quedó sin progreso en una suite; la ejecución fuera del sandbox terminó correctamente con los mismos datos sintéticos, sin DB habilitada.

## 8. Defecto real y correcciones locales

`importar-pa5-limpio.sh` usaba `test -z "$(docker … ls …)"`: el estado de `test` ocultaba el error del inventario, de modo que una salida vacía por fallo podía permitir continuar. Se separó la captura de cada consulta y su comprobación, conservando `set -e`, requisito de autorización, comprobación de vacío y todos los hashes.

Regresión previa: tres subcasos (imágenes/contenedores/volúmenes) fallaron con el original. Tras corregir, los tres conservan exit 8 y se detienen antes de consultar info/importar. Se añadieron pruebas sobre la ruta shell original para Id de índice correcto y rechazo de config/manifest como índice, Descriptor incorrecto, referencia Compose ausente, plataforma y rootfs incorrectos. Ninguna de estas pruebas contacta Docker real.

No se debilitaron restricciones ni cambiaron catálogos/binarios/digests. Los cambios y este informe se preparan para commit local revisable en la rama del PR; la identidad final y el estado limpio están en la evidencia de cierre. Los checks remotos corresponden al HEAD original; el nuevo commit local no tiene CI remoto porque no se hizo push.

PR #9: su directorio temporal ya no existe. La rama registrada y su referencia siguen en `1cb0d6becca26a87519aab7102f97f950f3d9570`; no se alteró ni reparó su worktree.

## 9. Matriz y gravedad

| Área | Resultado | Alcance / gravedad pendiente |
|---|---|---|
| Auditoría SSH sanitizada | PASS | Versiones, metadatos y Git observados; sin escrituras |
| SHA original e identidades OCI | PASS | Bytes offline; 33 blobs/29 capas |
| Paquetes/core/GDAL/LLVM en capas | PASS | No demuestra enlazado/JIT de un proceso real |
| Supuesta confusión config/index en verificador local | PASS | No se confirma defecto; regresión añadida |
| Inventario fallido en importador original | FAIL → PASS local | Garantía de aislamiento alta; corregido y probado |
| Importar preservando índice en Engine independiente | BLOCKED | Alta: no hay instancia autorizada |
| PostgreSQL 15.19/PostGIS 3.6.4/GDAL +pa5 efectivos | BLOCKED | Alta: no ejecutados en instancia desechable |
| Dependencias LLVM/JIT y smoke nativo | BLOCKED | Alta: sólo hashes offline |
| Referencias/renderizados Compose | PASS | No equivale a despliegue |
| Imagen +pa5 disponible en servidor | FAIL | Alta para despliegue; no afecta merge Git |
| 34 migraciones: gramática/igualdad con dev | PASS | Sin ejecución SQL |
| 34 migraciones reales y privilegios | BLOCKED | Alta: DB nueva/sintética pendiente |
| Backend integrado sobre +pa5 | BLOCKED | Alta: compatibilidad real pendiente |
| Cuatro checks offline remotos originales | PASS | No incluyen smoke omitido |
| Revalidación offline local corregida | PASS | 800 PASS/23 omitidos, sin DB |
| Git frente al dev remoto consultado | PASS | Mergeable y base integrada |
| SBOM/SCA de runtime instalado | NOT RUN | Pendiente antes de producción |
| Actualización/restauración de DB existente | NOT RUN | Alta; no inferir seguridad por major común |
| TLS/navegador/capacidad reales | NOT RUN | Pendientes de despliegue/producción |

## 10. Decisión

**NO MERGE por ahora.** No aparece un conflicto Git ni una regresión offline pendiente; la corrección del importador debe revisarse como commit local. El cierre estricto de esta evaluación requiere importación conservando identidad, smoke nativo y migraciones/roles/backend sobre instancia desechable autorizada. Se puede hacer sin GHCR con este mismo archivo, sin modificar hashes ni el daemon del proyecto.

Una eventual decisión de integrar sólo código con excepción de validación debe quedar explícitamente documentada por el propietario y ser compatible con las protecciones del PR. Esta auditoría no concede esa excepción. El estado actual tampoco autoriza desplegar sobre el servidor observado. No se ejecutó push, merge, publicación ni modificación del PR #9.
