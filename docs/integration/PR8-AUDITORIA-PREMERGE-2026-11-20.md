# PR #8 — Auditoría pre-merge sin GHCR

Fecha: 2026-11-20, America/Mexico_City. **Recomendación: NO MERGE por ahora.** La integración Git y los contratos offline aprueban; faltan la importación conservando identidad y las pruebas reales sobre instancia independiente desechable. GHCR no es una necesidad técnica de ese camino: puede sustituirse por el archivo congelado validado. No se concede una excepción ni se autoriza producción.

Estado más reciente: la sección 13 registra la corrección 035 ya validada; persiste el bloqueo del backend ABI39. Las secciones anteriores conservan resultados históricos.

Actualización: la sección 11 incorpora la segunda auditoría. Precisa el origen real del backend/frontend y sustituye las incertidumbres anteriores sobre el ledger por evidencia de metadatos de la base activa.

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

## 11. Segunda auditoría del despliegue SSALFER — 2026-11-20

**Conclusión actualizada: NO MERGE por ahora; sin bloqueo Git observado, con validación independiente pendiente.** Esta sección completa y corrige el alcance de las secciones 2 y 6: el checkout antiguo no identifica el backend activo, y ahora sí se inspeccionó el ledger real. No se repitieron las campañas aprobadas (800 PASS/23 omitidas de la primera auditoría); esos resultados conservan su fecha, alcance y límites.

### 11.1. Evidencia y alcance de lectura

Se utilizó únicamente `ssh -o BatchMode=yes -o ConnectTimeout=8 patrenes`, con la configuración autorizada preexistente. Se consultaron por separado ambos directorios, metadatos Docker seleccionados, hashes SHA-256 de código y versiones instaladas. SQL mediante el método anterior: `docker exec -i software-pa-db-1 sh -c '… psql -X -U "$POSTGRES_USER" -d db_integracion_mq_qa …'`, sin mostrar la identidad/credenciales configuradas. Todas las consultas SQL forzaron `default_transaction_read_only=on`, `statement_timeout=5000` y `lock_timeout=1000`; se comprobó `on` en la conexión.

No se leyeron registros de negocio, cuentas de aplicación, documentos, logs de servicios, archivos .env ni contenido del volumen protegido. Se consultaron únicamente roles técnicos, ACL, catálogos y filas del ledger explícitamente autorizadas. No hubo cambios en el servidor, Docker, permisos, Git remoto, bases o PR #9. No se arrancaron, detuvieron ni reconstruyeron servicios.

Evidencia nueva en `outputs/pr8-second-audit-20261120/` del worktree (ignorada por Git): scripts exactos transmitidos por stdin y respuestas sanitizadas `discovery.json`, `sources.json`, `database.json`, `compose-runtime.json`, `followup.json`, `final-observations.json`, `network.log`, `comparison.json`, `db-mount-comparison.json`, `missing-candidate-assets.json` y `remote-state.json`. `SHA256SUMS` identifica el expediente. Los scripts conservan las consultas; no contienen valores de credenciales.

### 11.2. Componentes y origen real

Abreviaturas: **O** = `/home/trenes/software-pa`; **M** = `/home/trenes/software-pa-integracion-mq`. Los cinco contenedores pertenecen al proyecto Compose `software-pa` y a la red bridge `software-pa_default` (`internal=false`, `172.18.0.0/16`). Compartir proyecto/red no implica compartir checkout ni invocación de Compose.

| Componente | Estado observado | Procedencia registrada al crearlo | Código/configuración visible y puertos efectivos |
|---|---|---|---|
| `frontend_ssalfer` | running, sin healthcheck | M: base + override + ssalfer; hash `ceda2054…` | Sin binds; estáticos y Nginx empaquetados en imagen. Host `0.0.0.0:80` y `[::]:80` → 80 |
| `backend` | running, healthy | M: base + override + ssalfer; hash `841053df…` | M/backend → `/app` RW; M/backend/uploads → `/app/uploads` RW. `127.0.0.1:8001` → 8000 |
| `db` | running, healthy | O: base + ssalfer; hash `a4abec1b…` | Volumen protegido `software-pa_postgres_data` → PGDATA; scripts/migraciones de O RO. `127.0.0.1:5433` → 5432 |
| `pgadmin` | running, healthy | M: base + override + ssalfer; hash `41663f1e…` | `software-pa_pgadmin_data` → `/var/lib/pgadmin`; `127.0.0.1:5050` → 80; 443 sin publicar |
| `frontend` anterior | exited (0) | O: base + ssalfer; hash `efaf5c3a…` | Sin binds ni puertos activos; no se inició para auditar |

IDs de imagen utilizados, completos en `discovery.json`:

- Backend: `sha256:6c1bda1c8d59d42303bd491f137e7d913449a056f96ca70d7d9288715833db93`.
- SSALFER: `sha256:24cc4d99fbcc7f408ace34bb383f351870d45d78321c5ce725a652c362ae373e`.
- DB: `postgis/postgis:15-3.3`, `sha256:a2fc46b52819d25add4ed93d3da83e106e17ea3ace6883cce3791631c9820bb2`.
- pgAdmin: digest fijado `sha256:40fa840c5bb7c8463957f1255b01283732c2d8c9396a956d180f8e6c296753b3`.
- Frontend detenido: `sha256:09b0287d8224f681196a23bf8c44a9645452a898d98f7a323e95acd787f54592`.

Backend efectivo, confirmado tanto en Config.Cmd/Path/Args como en `/proc/1/cmdline`:

```text
uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-proxy-headers --log-config /app/logging.json --no-access-log --reload
```

**`--reload` sigue activo.** El bind sobre `/app` sustituye el código empaquetado en esa ruta; el ID de imagen identifica el entorno de dependencias, no basta para atribuirle la versión del código activo.

### 11.3. Commits efectivos y comparación de archivos

| Estado | Rama / commit | Cambios locales observados |
|---|---|---|
| Checkout O | `feature/frontend-ssalfer-conectado`, `929fa135436066c6d3618f181d7e86cbca97065a` | `docker-compose.ssalfer.yml` modificado; un backup técnico no rastreado |
| Checkout M | `feature/integracion-mq-deploy`, `c1b4a00317c4915d0ae4a77e37de4c1b1af09f92` | `docker-compose.ssalfer.yml` modificado; una copia técnica no rastreada |
| B: dev remoto consultado | `c1b4a00317c4915d0ae4a77e37de4c1b1af09f92` | Referencia verificada mediante API GitHub |
| C: candidato local | `f715b55b964517aa4f859e9d20cbdcdee51a36ea` | Commit candidato conservado; se actualiza sólo documentación local |

Se compararon 194 archivos técnicos rastreados de O y 327 de M contra sus commits: la única diferencia dentro del inventario en cada checkout es el overlay SSALFER. No se inspeccionó el contenido de backups ni de otros archivos excluidos.

**Backend:** los 111 archivos inspeccionados dentro de `/app` (Python de app/scripts, migraciones, init, requirements, Dockerfile y logging) coinciden byte por byte con M y dev `c1b4a003…`. Frente a C coinciden 110; el Dockerfile cambia para construir GDAL. Las fuentes FastAPI de aplicación son iguales entre A/M, B y C. Esta equivalencia de fuentes visibles identifica el commit efectivo del código en disco; no es una inspección del bytecode ya cargado en memoria ni una attestación del build. No se reinició nada para obtener otra garantía.

**Frontend SSALFER:** 205 archivos en el document root; los 203 que tienen correspondencia en dev coinciden con `c1b4a003…`; los otros dos son `index.html` y `50x.html` de la imagen, sin correspondencia en el checkout inspeccionado. Nginx coincide con la configuración de dev. No hay etiqueta OCI revision/source en las imágenes backend/SSALFER; se atribuye su contenido por hashes, no por una etiqueta de commit inexistente.

Frente a C, el frontend conserva el bundle ExcelJS anterior; difieren `dashboard.html` y `js/resumenProyecto.js`, y no está el nuevo `exceljs-4.4.0-ssalfer.min.js`. Las ausencias adicionales de archivos vendor/documentación están enumeradas en `missing-candidate-assets.json`. Los recursos de seguimiento FIFONAFE y estilos de dashboard/resumen ya coinciden con dev/C; no se perdió esa funcionalidad al integrar el candidato. No se efectuó navegación ni prueba HTTP autenticada.

### 11.4. Mapa Compose: creación frente a disco actual

Las etiquetas registran **dos conjuntos separados**, cuya unión son cinco rutas:

1. O/docker-compose.yml + O/docker-compose.ssalfer.yml: DB y frontend anterior.
2. M/docker-compose.yml + M/docker-compose.override.yml + M/docker-compose.ssalfer.yml: backend, SSALFER y pgAdmin.

**No hay evidencia de que los cinco archivos se usaran juntos.** Hoy existen además otros archivos de override/producción: se encontraron ocho `docker-compose*.yml` entre ambos directorios. Existir en disco no demuestra haber participado en la creación de un contenedor.

Se renderizaron los archivos actuales con `--env-file /dev/null --no-interpolate --format json`, guardando sólo image/build/command/mounts/ports/profiles/platform/pull_policy/networks. No se resolvieron valores del .env. Los SHA-256 de archivos de disco y los config-hash de Docker tienen significados diferentes; no se comparan como si fueran el mismo hash.

Discrepancia concreta: el Compose actual de M declara DB `postgis/postgis:15-3.6@sha256:91098df…` y montajes de M, pero la DB activa conserva `15-3.3` y montajes de O. El puerto interpolado del backend tampoco se deduce del valor por defecto del YAML: el puerto **real** observado es 8001. Los overlays SSALFER modificados declaran publicación sin loopback; el estado real confirma el puerto 80 en todas las interfaces.

Montajes DB verificados también por hashes **dentro del contenedor**, sin acceder a PGDATA:

- O/backend/db/init/001_bootstrap_roles.sh → `/docker-entrypoint-initdb.d/001_bootstrap_roles.sh`, RO.
- O/backend/db/init/002_apply_migrations.sh → `/docker-entrypoint-initdb.d/002_apply_migrations.sh`, RO.
- O/backend/db/migrations → `/opt/software-pa/migrations`, RO: **sólo 001–011**.
- O/backend/scripts/run_migrations.sh → `/opt/software-pa/scripts/run_migrations.sh`, RO: runner antiguo.
- `software-pa_postgres_data` → `/var/lib/postgresql/data`, RW: protegido, no examinado como árbol de archivos.

No se debe reconstruir el despliegue con un `compose up` general para “conciliar” estas diferencias: podría sustituir DB/montajes o reutilizar el volumen protegido con otro runtime.

### 11.5. PostgreSQL, ledger y permisos observados

Base consultada: **`db_integracion_mq_qa`**, confirmada por `current_database()`. PostgreSQL efectivo 15.4; extensiones instaladas `postgis=3.3.4`, `btree_gist=1.7`, `plpgsql=1.0`. No aparece postgis_raster. GDAL de la DB: paquete libgdal28 `3.2.2+dfsg-2+deb11u2`; no se declara probado GDAL raster efectivo.

`public.schema_migrations` existe, con cuatro columnas NOT NULL: version (varchar), nombre (varchar), checksum_sha256 (char), aplicada_en (timestamptz). **34 filas, mínimo 001, máximo 034**. Nombres y hashes de las 34 coinciden exactamente con M, dev y C. En O sólo existen los primeros once archivos; esos once coinciden, pero faltan 012–034 en el montaje antiguo.

La fila 034 es `seguimiento_fifonafe_etiquetas`, SHA-256 `75e07a23e96da26d1a93a5ed90e9a3ad3990a58adc878b50ff9476f659bd1aef`. La tabla `etiqueta_seguimiento_fifonafe`, su secuencia y los triggers `trg_etiqueta_fifonafe_inmutable`/`trg_audit_etiqueta_fifonafe` existen; ambos triggers están habilitados (`O`). La función de inmutabilidad consultada contiene el rechazo de modificaciones esperado. El backend visible incluye el modelo, router y registro en main correspondientes, idénticos a dev/C. **034 está incorporada al código visible y al historial de la base**, aunque no al directorio de migraciones de la DB activa.

No se infiere quién aplicó 012–034 ni desde qué herramienta; el ledger no prueba esa procedencia histórica. Tampoco se afirma equivalencia completa de todo el esquema por comprobar ledger y objetos seleccionados.

Roles/privilegios, sin mostrar nombres de login ni claves:

- La conexión de auditoría usa el rol propietario/superusuario configurado; las consultas están restringidas a lectura.
- El runtime declarado por el backend coincide con el runtime de la DB y es distinto del propietario; no hay fallback DB_USER configurado.
- Runtime: LOGIN/INHERIT; sin superusuario, CREATEDB, CREATEROLE, replicación ni BYPASSRLS; miembro de `software_pa_app`. Grupo NOLOGIN.
- Runtime tiene USAGE de public y no CREATE; no es propietario de las cinco tablas seleccionadas. Puede leer ledger y no INSERT/UPDATE/DELETE/TRUNCATE sobre él. No DELETE/TRUNCATE sobre las otras tablas consultadas.
- Sobre etiquetas tiene SELECT/INSERT y **también UPDATE por privilegios por defecto**. Se confirmó el default ACL que concede UPDATE a software_pa_app; el trigger BEFORE UPDATE/DELETE contiene el rechazo. No se presenta un GRANT SELECT/INSERT como revocación del UPDATE heredado. Esto coincide con la combinación de baseline y 034; el comportamiento efectivo del rechazo sigue pendiente de ensayo sintético. No se probó con una escritura en la base activa.

El runner antiguo montado conserva `2>/dev/null || true` al consultar checksums. El candidato/dev tienen el guard corregido. Su presencia es un riesgo operativo del despliegue actual; no se ejecutó, no se corrigió en el servidor y no es un nuevo defecto del candidato.

### 11.6. Comparación A/B/C y clasificación de riesgos

| Área | A: servidor efectivo | B: dev `c1b4a003` | C: candidato `f715b55` | Implicación |
|---|---|---|---|---|
| FastAPI app | Fuentes visibles coinciden con B | Modelo MQ/FIFONAFE actual | App idéntica a B | Sin divergencia funcional nueva detectada por hashes |
| Dashboard/resumen | Recursos B, bundle ExcelJS antiguo | Igual A | Bundle reconstruido y corrección de carrera del diálogo | Requiere probar frontend C; A no acredita esas novedades |
| FIFONAFE/034 | Código B; ledger/objetos 034 presentes | 034 canónica | Mismos SQL/app | Resuelta la incertidumbre sobre incorporación al activo |
| Migraciones montadas/runner | O, 11 SQL y runner antiguo | 34 SQL y guard actual | Igual B | Alta: procedencia de despliegue incoherente |
| DB runtime | PG15.4/PostGIS3.3.4 | Compose declara 15-3.6 fijado | +pa5 PG15.19/PostGIS3.6.4 | Alta: ningún reemplazo fue validado aquí |
| GDAL backend | CLI `/usr/bin/gdalinfo`/ogrinfo 3.10.3, libgdal36 Debian sin +pa5 | Dockerfile instala gdal-bin Debian | Construye GDAL3.13.3 ABI39 /opt/gdal | Alta: A no valida las librerías/drivers de C |
| Python dependencias muestreadas | Python3.11.18; FastAPI0.138.2, Starlette1.3.1, Uvicorn0.49.0, SQLAlchemy2.0.51, psycopg2-binary2.9.12 | Pins coincidentes | Mismos pins | Muestreo de versiones, no SCA/SBOM completo |
| Compose/montajes | Dos checkouts; bind /app RW, uploads bind | Override de desarrollo disponible | Base cambia DB, pgAdmin pasa a perfil opcional | Alta para despliegue; no conflicto Git |
| Seguridad efectiva | APP_ENV development, cookie Secure=false, SameSite=lax; --reload; HTTP80 en todas las interfaces; red no interna | Configuración prod requiere selección explícita | Mantiene perfiles y añade hashes CSP report-only | No acreditar producción/TLS por tener controles en Git |

No se verificaron firewall, accesibilidad desde Internet ni terminación TLS externa: escuchar en todas las interfaces no demuestra exposición pública a Internet. Los controles de producción del repositorio no son los parámetros efectivos del despliegue inspeccionado. La ausencia de bindings Python osgeo en el backend no es por sí sola un fallo: esta aplicación usa herramientas CLI; éstas sí respondieron con GDAL3.10.3.

B es ancestro de C. El PR remoto continúa abierto/draft con HEAD `8dcaf74…` y `mergeable=true`; C permanece sólo local. **Los cuatro checks remotos anteriores no validan `f715b55`.** Los resultados locales anteriores sí incluyen la corrección local, dentro de su alcance offline. Ningún hallazgo justifica repetir ahora las 800 pruebas ni modificar el código del candidato.

### 11.7. VM independiente en Cooper: propuesta pendiente

No se identificó un Engine desechable autorizado: en patrenes sólo `default`, Engine protegido `38a3bf79-1712-4ce7-a5d7-a23d15d6395a`; localmente sólo `default` del proyecto. No se intentó aprovisionar o reconfigurar ninguno. No se tiene acceso confirmado al inventario de Cooper ni se afirma disponibilidad de una VM allí.

Configuración propuesta para una **VM nueva dedicada** en Cooper, condicionada a su disponibilidad y autorización; dimensionamiento inicial, no capacidad medida:

- Linux amd64; Ubuntu Server 24.04 LTS es una opción para acercarse al host observado. 4 vCPU, 8 GiB RAM y 60 GiB de disco libre inicial para archivo, capas descomprimidas, caché de build de backend y datos sintéticos. Aumentar si el build lo requiere; tmpfs/PGDATA deben quedar acotados a la RAM disponible.
- Docker Engine instalado y con versión fijada/revisada, almacén containerd confirmado mediante `docker info`; Compose >=2.24.4. Registrar Engine ID distinto de patrenes y del Engine local protegido. No basta cambiar de contexto o apuntar al mismo socket por SSH.
- Disco nuevo, sin montajes compartidos de Docker/PGDATA/uploads del proyecto, sin conexión a sus bases ni credenciales institucionales. Almacén Docker inicialmente vacío; no limpiarlo a la fuerza si ya contiene recursos. SSH con identidad autorizada de esa VM; sin inventar alias/IP.
- Transferir el archivo +pa5 congelado y el checkout **exacto f715b55**; comprobar SHA original y todos los hashes del catálogo. Preparar herramientas y bases de build fijadas antes de aislar las pruebas. Las descargas necesarias del build del backend requieren una política de red propia; no necesitan GHCR. Nunca reconstruir el artefacto +pa5 para evadir un fallo de identidad.
- Ejecutar importador corregido y verificador originales; exigir índice/config/manifest, plataforma, RepoDigests y librería exactos. Después smoke nativo en contenedor propio sin red, con tmpfs y usuario postgres.
- Crear nueva DB sintética, bootstrap de roles, migraciones 001–034, comprobar ledger/checksums, segunda ejecución sin reaplicar, permisos y rechazo efectivo de UPDATE/DELETE sobre etiquetas. Estas últimas pruebas escriben y sólo se autorizan dentro de esa instancia.
- Construir/validar el backend C, con GDAL3.13.3 ABI39 separado de GDAL ABI36 de PostGIS. Ejecutar backend/roles/GIS/FIFONAFE con runtime sintético y uploads efímeros sobre una red privada sin puertos publicados.
- Renderizar Compose con variables sintéticas; después validar frontend C, nuevo ExcelJS, resumen y perfiles de seguridad. Preparar evidencia de cada comando y código de salida. El procedimiento ya preparado en `PR8-PROCEDIMIENTO-DESECHABLE-2026-11-20.md` continúa aplicando.

La VM no valida por sí sola la actualización del volumen existente. Esa etapa necesita un ensayo adicional sobre copia restaurada autorizada, respaldo/verificación de recuperación, compatibilidad de extensiones, procedencia del ledger, montajes correctos y reversión. El volumen original permanece protegido.

### 11.8. Matriz final de esta segunda auditoría

| Verificación | Estado | Límite |
|---|---|---|
| Separar ambos Git y sus modificaciones | PASS | Checkout O no es el backend activo |
| Etiquetas, cinco archivos asociados y montajes efectivos | PASS | Configuración de creación y disco actual distinguidos |
| Hashes de fuentes backend/frontend frente a dev/C | PASS | Equivalencia en disco; sin attestación de build ni memoria |
| Presencia efectiva de --reload | PASS: confirmado | Riesgo operativo para producción |
| PG/PostGIS y extensiones actuales | PASS | No son los runtimes +pa5 |
| Ledger 001–034 frente a MQ/dev/C | PASS | Metadatos; no ejecución nueva de migraciones |
| Incorporación de 034 y objetos seleccionados | PASS | Rechazo funcional del trigger no ensayado |
| Roles/ACL/propiedad seleccionada | PASS | Catálogos; sin prueba de escritura/autenticación |
| Montaje DB coherente con código activo | FAIL | Sólo 11 SQL y runner antiguo en DB |
| Backend nativo C / DB +pa5 independientes | BLOCKED | Falta Engine/VM autorizados |
| Migraciones nuevas y backend/roles sintéticos | BLOCKED | No reemplazadas por lectura del ledger del servidor |
| CI remoto de f715b55 | NOT RUN | Commit sólo local; sin push |
| Browser/TLS/capacidad/SCA instalados de C | NOT RUN | Sin extrapolar desde las versiones observadas |

### 11.9. Recomendación fundamentada

**NO MERGE por ahora.** Se resuelven dos discrepancias relevantes: el backend/frontend activos proceden de MQ/dev `c1b4a003`, y la migración034 sí está en su código e historial. No hay diferencia entre las migraciones/FastAPI de B y C que sugiera un conflicto Git nuevo. El riesgo pendiente principal sigue siendo el runtime nativo C no validado en instancia independiente; la lectura del servidor antiguo no sustituye esa prueba.

Para despliegue existe además una incoherencia demostrada entre procedencia de servicios, scripts montados y ledger. Debe resolverse en un plan separado probado en copia, sin tocar ahora el servidor. No se autoriza un arranque general de Compose ni migrar el volumen protegido. No hubo push, merge, publicación GHCR, cambio remoto ni modificación del PR #9. El candidato permanece `f715b55`; la documentación local del expediente incorpora esta segunda auditoría.


## 12. Validación nativa PA5-QA — 2026-11-20

**NO MERGE: hallazgo de seguridad reproducido.** La etapa nueva ejecutó sobre el Engine autorizado `9efbaf92-7703-4fa0-9192-31b975794366` el smoke original completo mediante Python externo RO, bootstrap, migraciones 001–034, comparación exacta del ledger, 34 verificaciones sin reaplicación, contrato ACL existente, 16 operaciones prohibidas y triggers UPDATE/DELETE de 034 con rollback. Esas comprobaciones específicas aprobaron, sin modificar imagen ni migraciones.

La ampliación de seguridad detectó TEMP permitido y un desvío real de `fn_audit_log()`: con una `bitacora` temporal homónima, una inserción sintética produjo `public.bitacora=0` y `pg_temp.bitacora=1`. Todo se revirtió. El launcher final termina con código 1 y estado FAIL; no se declara aprobada la integridad de auditoría. El defecto está también en el baseline de dev; no se ensayó contra patrenes.

Queda preparado el plan de backend GDAL 3.13.3 ABI39, pero no se ejecutó por falta de imagen/suministro offline autorizado. No se hizo pull/build ni se cambió conectividad. El commit candidato sigue f715b55; la corrección de auditoría requiere un cambio nuevo revisado, sin editar las migraciones históricas.

Informe y propuesta de corrección pendiente: [validación nativa](PR8-VALIDACION-NATIVA-PA5-QA-2026-11-20.md). Herramientas reproducibles: `tests/qa/pa5_native_premerge/`. Evidencia nueva y códigos: `outputs/pr8-native-pa5-qa-20261120/`, con `summary-final.json` y `evidence-gate/result.json` como resultados finales. No confundirlos con el resumen inicial anterior al hallazgo TEMP. Las restricciones del servidor y del PR #9 se conservaron; no hubo push ni merge.


## 13. Corrección 035 — 2026-11-20

El defecto de auditoría detectado en la etapa anterior quedó corregido mediante `035_endurecer_auditoria_search_path.sql`, sin editar001–034 ni cambiar permisos globales. Se revisaron las cuatro definiciones históricas de la única función SECURITY DEFINER de aplicación y se calificaron sus seis tablas persistentes, con `pg_catalog, public, pg_temp`. También se rechaza vincular esa función a triggers de tablas temporales.

En PA5-QA (Engine9efbaf92-7703-4fa0-9192-31b975794366), las regresiones estrictas fallaron antes y aprobaron después: INSERT/UPDATE pasó de public=0/temp=2 a public=2/temp=0; trigger temporal propio rechazado. Aprobaron autenticación SQL, roles, inmutabilidad034 y rollback, tanto en una DB nueva001–035 como en una sintética001–034 actualizada. Ledger35 exacto y segundo pase35 verificadas/0 reaplicadas. Owner/ACL/OID/datos y TEMP preservados;60 tests offline afectados aprobados. Imagen congelada y archivo intactos, sin patrenes ni bases existentes.

**Recomendación global: NO MERGE todavía por el backend GDAL3.13.3 ABI39 no ejecutado.** El bloqueo de integridad de auditoría está resuelto; los resultados FAIL previos se conservan como evidencia roja histórica. No hubo push/merge ni modificación del PR#9.

Informe y matriz actuales: [corrección035](PR8-AUDITORIA-035-2026-11-20.md). Suministro backend declarado y faltantes: [manifiestoABI39](PR8-BACKEND-ABI39-SUMINISTRO-2026-11-20.json). Evidencia: `outputs/pr8-audit035-20261120/`.
