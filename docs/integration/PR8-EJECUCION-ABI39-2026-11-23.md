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
| CI remoto del nuevo HEAD | Pendiente de publicación al crear este commit; consultar checks del SHA publicado |
| Recompilación nativa independiente / reproducibilidad bit a bit | NOT RUN; no se declara |
| Merge y despliegue | NO REALIZADOS |

## Correcciones verificadas

Las dos expectativas de `/health` aún exigían esquema 30; ahora exigen exactamente 35. La regresión de subida se reutiliza íntegra desde un módulo independiente: el savepoint del catálogo mantenía locks de escritura incompatibles con el `SHARE NOWAIT` de autorización. Se conservan sus comprobaciones de subida 201, duplicado 409, SHA-256 y descarga byte por byte. No se desactiva ningún guard, lock ni trigger y no se omite el caso.

Los fallos de ejecución anteriores permanecen registrados: import OCI parcial sin attestations; permisos _apt sobre el mirror privado; ejecutables de prueba en tmpfs noexec; pool con overflow 0 y SECRET_KEY ausente en el ejecutor; clúster de smoke SQL sin UTF8. Se corrigieron únicamente las herramientas/fixtures del laboratorio. UTF8 explícito eliminó los HTTP 500 por codificación y permitió comprobar realmente API/GIS. El ejecutor final devuelve error si cualquier etapa falla.

## Suministro y recursos observados

Adquisición mediante Python stdlib del host PA5-QA; apt/pip resuelven dentro de la base trixie/cp311 con `--network none`. No se instalaron paquetes en el host. GDAL se copió del tar local y conservó SHA-256 `5e0c388d83da2d686cc00a40272882432cdb54edff43d4af173e532844a0a0ea`.

Se recibieron **323,859,727 bytes HTTP**, más una reserva conservadora de 128 MiB para entradas locales: dentro de 5 GiB. Disco: **4,417,984 KiB como cota conservadora**, sumando árbol de tarea, DockerRootDir y **todo** `/var/lib/containerd`, incluido lo preexistente; dentro de 20 GiB. DockerRootDir por sí solo no cubre este Engine con snapshotter containerd. Compilación con 2 trabajos y límite de 3 GiB RAM.

El builder clásico consumió la base local por digest y los cierres adquiridos, con `DOCKER_BUILDKIT=0`, `--pull=false` y `--network none`. La receta offline, locks y hashes observados acompañan este informe. Los empaquetados posteriores reutilizaron las capas nativas propias; el payload completo `/opt/gdal` y `/app/app` coincide con el primer build. Esto no demuestra una recompilación independiente ni reproducibilidad bit a bit. La imagen QA contiene los insumos públicos de suministro en sus capas; no se presenta como una imagen mínima de producción ni como un SCA completo.

## Evidencia y decisión

[Evidencia seleccionada y checksums](pr8-abi39-20261123/SHA256SUMS), [resultado máquina](pr8-abi39-20261123/execution-result.json), [pytest real](pr8-abi39-20261123/logs/backend-api-pytest.log), [pruebas nativas](pr8-abi39-20261123/logs/backend-native.log), [HTTP real](pr8-abi39-20261123/logs/uvicorn-auth.log). Evidencia íntegra local, incluidos intentos fallidos: `outputs/pr8-backend-executed-20261123/` (290 archivos, SHA256SUMS). Claves, envs, sockets, bases y uploads excluidos.

El bloqueo técnico del backend ABI39 queda resuelto para el alcance ejecutado. Publicar este candidato y comprobar el CI del SHA resultante; no atribuirle checks de otro HEAD. Un job omitido, pendiente o fallido no es PASS. No integrar si queda una validación obligatoria sin ejecutar. No se modificaron patrenes, Docker original de Cooper, PR #9, +pa5, migraciones, configuración Docker/WSL o redes. No se despliega ni se realiza merge desde esta ejecución.
