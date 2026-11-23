# Procedimiento pendiente — instancia desechable +pa5

Preparado el 2026-11-20; **NO EJECUTADO**. No es autorización de un endpoint ni evidencia de éxito. No utilizar el Engine local del proyecto ni `patrenes`.

## Preparación obligatoria

1. Obtener un endpoint expresamente autorizado como desechable, Linux amd64, con almacén containerd. Registrar su Engine ID y compararlo con el Engine protegido local y con el servidor `38a3bf79-1712-4ce7-a5d7-a23d15d6395a`. Un contexto diferente no demuestra independencia. No modificar ningún daemon para fabricar el entorno.
2. En una sesión aislada fijar `DOCKER_HOST` al endpoint autorizado, eliminar `DOCKER_CONTEXT` y cualquier configuración que redirija comandos. Conservar la configuración TLS necesaria sin imprimirla. Volver a comprobar Engine ID antes de cada fase mutante y antes de limpiar recursos propios. Detenerse si cambia.
3. Ejecutar por separado `docker image ls -aq`, `docker ps -aq`, `docker volume ls -q`, comprobando el éxito de cada consulta y su salida vacía. No vaciar un Engine existente.
4. Usar el checkout corregido auditado, comprobar el SHA-256 del archivo original y suficiente espacio para OCI y PostgreSQL. Registrar versión Engine/Compose y comandos de la prueba.

## Importación y smoke originales

Sólo tras completar las condiciones anteriores:

```sh
archive=/home/alfredo/proyectos/software-pa-recuperacion-pr6-20261111/etapa4r-desbloqueo-20261118/artefactos/pa5-validated-image.tar
reference=software-pa-libgdal36-candidate:20261117-pa5@sha256:d413671654deef3c43367ea3fd0be56a32a36d75b9d971970e33ec56a76b7c3c
PA5_DISPOSABLE_ENGINE_APPROVED=yes sh deploy/ci/importar-pa5-limpio.sh "$archive"
sh deploy/ci/verificar-pa5-engine.sh "$reference"
docker run --rm --pull never --network none --read-only --user postgres \
  --tmpfs /tmp:rw,nosuid,nodev,mode=1777 --cap-drop ALL \
  --security-opt no-new-privileges:true \
  -v "$PWD/deploy/ci:/qa:ro" --entrypoint sh "$reference" /qa/pa5-native-smoke.sh
```

No reconstruir ni retaggear para resolver errores; conservar el índice y las attestations. Guardar salida/código de cada comando. El smoke comprueba versiones de paquetes exactas, hashes de GDAL/core/bitcode, GDAL MEM real, extensiones PostGIS/raster, geometría y JIT con inlining. La comparación de PostgreSQL SQL sólo exige major 15; el chequeo exacto 15.19 procede del paquete. Añadir `SHOW server_version` para registrar también la versión efectiva.

## Migraciones y backend

En otro contenedor propio de esa misma imagen, con red inicialmente deshabilitada y PGDATA exclusivamente en tmpfs:

1. Montar `backend/db/migrations`, `backend/db/init` y `backend/scripts` del checkout auditado como sólo lectura. Inicializar PostgreSQL con `initdb -U qa_owner`, socket privado y `listen_addresses=''`; registrar `SHOW server_version`, `postgis_full_version()` y la versión efectiva de GDAL raster después de crear extensiones. Usar únicamente claves sintéticas efímeras.
2. Crear la base **nueva** `software_pa_test`; exportar `POSTGRES_USER=qa_owner`, `POSTGRES_DB=software_pa_test`, `DB_RUNTIME_USER=qa_runtime`, `DB_RUNTIME_PASSWORD` sintética y `PGHOST` al socket privado. Ejecutar primero `001_bootstrap_roles.sh`, luego `run_migrations.sh` con `MIGRATIONS_DIR` al montaje. No usar la identidad runtime para aplicar DDL.
3. Exigir exactamente 34 filas de `schema_migrations` con sus nombres/checksums canónicos, repetir el runner y comprobar que verifica sin reaplicar. Ensayar rechazos de ledger alterado/ausente/con huecos únicamente en copias sintéticas separadas. No modificar hashes canónicos.
4. Conectar como runtime y ejecutar comprobaciones de `backend/tests/test_runtime_postgresql.py`: identidad propia, pertenencia al grupo, ausencia de superusuario/creación de roles/DB/BYPASSRLS, ausencia de propiedad de objetos y rechazo de DDL y de escritura del ledger. Revisar los grants nuevos de 034.
5. Para pytest de API, preparar la imagen backend exacta del checkout (su GDAL ABI39 es distinto del ABI36 de PostGIS) y una red privada **del Engine desechable**, sin puertos publicados. Sólo entonces habilitar TCP interno para la nueva base. Crear el seed sintético que requieren los fixtures; no copiar cuentas o documentos del servidor.
6. Dentro del backend fijar `APP_ENV=test`, `DB_NAME=software_pa_test`, `TEST_ALLOW_DATABASE=software_pa_test`, runtime/clave sintéticos, `DB_HOST` al contenedor propio y `UPLOAD_ROOT` efímero. Ejecutar las suites runtime, auth/RBAC, documentos, consultas dashboard/FIFONAFE y GIS; después ampliar a `backend/tests`. El linaje histórico exige su propia instancia con marcador `software-pa-lineage-equivalence`, no se habilita poniendo sólo una variable.
7. Renderizar las tres selecciones Compose con `--env-file` sintético y revisar referencia, plataforma, `pull_policy: never`, puertos y montajes. No arrancar el Compose del proyecto para esta prueba.
8. Registrar resultados, fallos y omisiones. Destruir sólo contenedores/redes/recursos propios identificados, tras volver a verificar Engine ID. No ejecutar prune ni eliminar volúmenes ajenos.

Estos pasos no validan una actualización del volumen del servidor. Ese cambio requiere respaldo/restauración ensayados, inventario de extensiones, revisión de linaje/checksums, permisos y plan de reversión por separado.
