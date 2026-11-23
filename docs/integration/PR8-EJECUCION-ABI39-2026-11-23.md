# PR #8 — Ejecución ABI39 en PA5-QA, 2026-11-23

Backend construido y validado realmente. Base fuente `671db9750047831b9543e2867ad4a20251cb076f`, con las correcciones de pruebas incluidas en este commit. Aplicación y migraciones 001–035 sin cambios respecto a 671db97.

- Engine comprobado antes de cada operación Docker: `9efbaf92-7703-4fa0-9192-31b975794366`.
- Imagen local: `software-pa-backend-qa:671db97-abi39-acceptance`.
- ID local: `sha256:f6c729cc2047d5795c98f3daccd747380ec25538e747687f37b6159b21bf7264`. No es un digest de registro publicado.
- Plataforma linux/amd64; Python 3.11.18; GDAL 3.13.3 ABI39; UID/GID 10001. ABI36 no se carga en el backend; PostGIS usa +pa5 en otro contenedor.

| Comprobación ejecutada | Resultado |
|---|---|
| Base Python: raíz, manifest amd64, config, capas/diff_ids, import e identidad | PASS |
| apt trixie/amd64: firmas y cierre; 171 paquetes build y 46 runtime; instalación offline | PASS |
| Python cp311/amd64: 38 wheels runtime y 43 QA; hashes, resolver nativo, instalación offline y pip check | PASS |
| Build GDAL/backend, sin pull y RUN sin red | PASS |
| SQL fresh 001–035 y upgrade 001–034 → 035, cada uno en clúster nuevo | PASS |
| Ledger canónico, roles, auditoría persistente/auténtica, FIFONAFE/034; repetición: 35 verificadas y 0 reaplicadas | PASS |
| Seguridad Python local equivalente a las suites CI: 35 suites, 638 pruebas, sin skips | PASS |
| Backend: autenticación, runtime/RBAC, GIS, FIFONAFE, catálogo documental y versiones: 190 pruebas | PASS |
| GDAL nativo: 5 pruebas de drivers/round trips/rechazos; carga explícita .so.39 y exclusión .so.36 | PASS |
| Uvicorn real con comando candidato: health/root, login, sesión, CSRF ausente rechazado y logout | PASS |
| Limpieza de contenedores propios; +pa5 y redes host/none conservados | PASS |
| CI remoto de 15f42c4 | 4 jobs SUCCESS; registry/native smoke SKIPPED; comprobar cada HEAD posterior |
| Recompilación nativa independiente, contexto nuevo y --no-cache | PASS; payloads iguales por SHA-256, aceptación repetida |
| Identidad de imagen OCI bit a bit | No se afirma: los IDs OCI difieren |
| Merge y despliegue | NO REALIZADOS |

## Correcciones verificadas

Las dos expectativas de `/health` aún exigían esquema 30; ahora exigen exactamente 35. La regresión de subida se reutiliza íntegra desde un módulo independiente: el savepoint del catálogo mantenía locks de escritura incompatibles con el `SHARE NOWAIT` de autorización. Se conservan sus comprobaciones de subida 201, duplicado 409, SHA-256 y descarga byte por byte. No se desactiva ningún guard, lock ni trigger y no se omite el caso.

Los fallos de ejecución anteriores permanecen registrados: import OCI parcial sin attestations; permisos _apt sobre el mirror privado; ejecutables de prueba en tmpfs noexec; pool con overflow 0 y SECRET_KEY ausente en el ejecutor; clúster de smoke SQL sin UTF8. Se corrigieron únicamente las herramientas/fixtures del laboratorio. UTF8 explícito eliminó los HTTP 500 por codificación y permitió comprobar realmente API/GIS. El ejecutor final devuelve error si cualquier etapa falla.

## Suministro y recursos observados

Adquisición mediante Python stdlib del host PA5-QA; apt/pip resuelven dentro de la base trixie/cp311 con `--network none`. No se instalaron paquetes en el host. GDAL se copió del tar local y conservó SHA-256 `5e0c388d83da2d686cc00a40272882432cdb54edff43d4af173e532844a0a0ea`.

Se recibieron **323,859,727 bytes HTTP**, más una reserva conservadora de 128 MiB para entradas locales: dentro de 5 GiB. Disco: **4,417,984 KiB como cota conservadora**, sumando árbol de tarea, DockerRootDir y **todo** `/var/lib/containerd`, incluido lo preexistente; dentro de 20 GiB. DockerRootDir por sí solo no cubre este Engine con snapshotter containerd. Compilación con 2 trabajos y límite de 3 GiB RAM.

El builder clásico consumió la base local por digest y los cierres adquiridos, con `DOCKER_BUILDKIT=0`, `--pull=false` y `--network none`. La receta offline, locks y hashes observados acompañan este informe. Los empaquetados posteriores reutilizaron las capas nativas propias; el payload completo `/opt/gdal` y `/app/app` coincide con el primer build. Esos primeros empaquetados no demuestran una recompilación independiente. La reconstrucción posterior descrita abajo sí vuelve a compilar sin caché; no se afirma identidad OCI bit a bit. La imagen QA contiene los insumos públicos de suministro en sus capas; no se presenta como una imagen mínima de producción ni como un SCA completo.

## Reconstrucción independiente completada

Sobre el código de `15f42c42cd89ea0bb4499e1db9fa7f6096c255db`, se verificaron 552 archivos de entrada, se creó otro contexto y se ejecutó el builder clásico con `--no-cache --pull=false --network none`, 2 trabajos CMake y 3 GiB RAM. El log no contiene hits de caché. No se descargaron dependencias nuevas.

Imagen independiente: `software-pa-backend-qa:15f42c4-abi39-independent`, ID `sha256:88adea76ddb46b735f1079c0ad3d9d050f5c0c1c11aa0e406e419daa73af52cb`.

La comparación SHA-256 no encontró diferencias en los **373 archivos GDAL**, **55 archivos de aplicación**, **5,575 archivos Python instalados excluyendo .pyc/.pyo**, **61 bibliotecas ELF enlazadas**, 131 registros apt y 41 distribuciones Python. UID/GID 10001, Python 3.11.18 y plataforma también coinciden. Los metadatos OCI y los .pyc no forman parte de esta afirmación; los IDs de imagen son diferentes.

Sobre el segundo ID real se repitieron las **190 pruebas de integración y 5 nativas**, más health/root/login/sesión/CSRF/logout contra Uvicorn: PASS. Otro clúster sintético UTF8 con 001–035, socket y claves nuevos; sus contenedores fueron eliminados al terminar. No sumar esos reintentos como nuevas pruebas únicas.

Contador HTTP inalterado: 323,859,727 bytes. La cota conservadora final de disco sube a **7,095,220 KiB (6.77 GiB)**, incluyendo todo containerd preexistente: sigue debajo de 20 GiB. +pa5 conserva su digest y las redes siguen siendo host/none.

[Comparación y fingerprints](pr8-abi39-20261123/independent-build-comparison.json), [segunda aceptación](pr8-abi39-20261123/api-qa-independent/result.json), [190 pruebas repetidas](pr8-abi39-20261123/logs-independent/backend-api-pytest.log). Inventarios completos y log de compilación: `outputs/pr8-backend-executed-20261123/independent/`, con SHA256SUMS.

El CI remoto de `15f42c4` terminó con cuatro jobs SUCCESS; el transporte GHCR/registry-native quedó SKIPPED por borrador. Ese job consume PostgreSQL desde un registro y exige un Engine vacío; no es una prueba del backend ABI39. No se ejecutó en otro Engine ni se retiraron imágenes del laboratorio para satisfacerlo. El 403 del conector para editar la metadata de #8 permanece registrado; no se presenta como un fallo del backend ni como una autorización pendiente de adquisición/build/pruebas.

## Evidencia y decisión

[Evidencia seleccionada y checksums](pr8-abi39-20261123/SHA256SUMS), [resultado máquina](pr8-abi39-20261123/execution-result.json), [pytest real](pr8-abi39-20261123/logs/backend-api-pytest.log), [pruebas nativas](pr8-abi39-20261123/logs/backend-native.log), [HTTP real](pr8-abi39-20261123/logs/uvicorn-auth.log). Evidencia íntegra local, incluidos intentos fallidos: `outputs/pr8-backend-executed-20261123/` (290 archivos, SHA256SUMS). Claves, envs, sockets, bases y uploads excluidos.

El bloqueo técnico del backend ABI39 queda resuelto, incluida la recompilación independiente para el alcance medido. La integración de código a dev tiene evidencia nativa y funcional favorable por la ruta local validada; esto no acredita distribución GHCR ni despliegue. Publicar este candidato y comprobar el CI del SHA resultante; no atribuirle checks de otro HEAD. Un job omitido, pendiente o fallido no es PASS. No integrar si queda una validación obligatoria sin ejecutar. No se modificaron patrenes, Docker original de Cooper, PR #9, +pa5, migraciones, configuración Docker/WSL o redes. No se despliega ni se realiza merge desde esta ejecución.
