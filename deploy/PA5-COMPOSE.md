# Candidato local +pa5 y Compose — 2026-11-18

Etapa 4 selecciona exclusivamente `software-pa-libgdal36-candidate:20261117-pa5@sha256:d413671654deef3c43367ea3fd0be56a32a36d75b9d971970e33ec56a76b7c3c`, plataforma `linux/amd64`, con `pull_policy: never`. No hay fallback a imágenes públicas ni a +pa2/+pa3/+pa4. El índice OCI coincide con F2-E1; el manifest amd64 es `sha256:27e9ca0702414c9515cf205df5635af7ad7509385dffcf7dcf6fb048c185f9b7` y el config digest es distinto. No intercambiar esas identidades.

Esta referencia existe sólo en el Docker Engine validado. Un entorno limpio no puede descargarla. Antes de CI o QA en otro Engine hace falta distribuir un archivo OCI con índice/manifests/blobs y sus hashes, verificarlo al importar y comprobar que la referencia exacta resuelve al índice esperado; alternativamente, publicar en un registro autorizado y fijar su digest tras verificar equivalencia. Docker save/load requiere demostrar que conserva/resuelve el índice con attestations: no se da por supuesto. No se exportó, importó, publicó ni reconstruyó ninguna imagen en esta etapa. El aprovisionamiento es un bloqueo de distribución, no un motivo para permitir pull o cambiar el digest.

La base mantiene PostgreSQL 15.19, PostGIS 3.6.4, core histórico y bitcode LLVM. GDAL ABI36 `3.10.3+dfsg-1+pa5` pertenece a PostGIS; el backend compila GDAL 3.13.3 ABI39 en `/opt/gdal` sobre Debian trixie fijado y conserva sus drivers restrictivos. No montar ni copiar bibliotecas de uno al otro. Las recetas nativas históricas se conservan como procedencia; no son un build activo de Compose. F2-E1 contiene la receta temporal efectiva y sus diferencias, no se afirma reconstrucción desde cualquier receta antigua.

Selecciones declarativas, sin ejecutar servicios:

```sh
docker compose --env-file /ruta/env-sintetico -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.ssalfer.yml config
docker compose --env-file /ruta/env-sintetico -f docker-compose.yml -f docker-compose.ssalfer.yml -f docker-compose.prod.yml config
```

Producción requiere Compose >= 2.24.4 por `!reset`, variables reales adecuadas y certificados provisionados por el procedimiento TLS revisado. No combinar override de desarrollo con prod. Producción publica sólo 80/443, conserva red interna y volúmenes `postgres_data`/`uploads_data`; backend y DB dependen de readiness de DB y API. El frontend no declara healthcheck propio: su disponibilidad HTTP real y los certificados requieren QA posterior. Los límites actuales son DB 1 GiB y backend 2 GiB/160 PIDs/dos workers; son una configuración conservada, no una prueba de capacidad.

pgAdmin conserva imagen por digest, volumen y dependencia de DB saludable, en el perfil opcional `admin-tools`. No es dependencia de la aplicación. Desarrollo publica sólo loopback:5050; producción elimina su puerto incluso si se activa el perfil. Comparte la red de DB (interna en prod). Las variables PGADMIN_DEFAULT_EMAIL/PASSWORD vacías permiten renderizar Compose sin secretos administrativos; la imagen debe rechazar su arranque sin credenciales válidas. No se establece una contraseña de reserva. Activar pgAdmin requiere credenciales propias y acceso local/túnel autorizado; no se recomienda activar ese perfil en producción. La autenticación efectiva y el rechazo de credenciales vacías no se ensayaron con un contenedor en Etapa 4.

El arranque de una DB nueva ejecutaría scripts init/migraciones, y no queda autorizado por `config`. No se arrancaron servicios, ejecutaron migraciones ni alteraron datos. La base Git sigue atrasada frente a dev: el test dashboard-performance tiene cambios en ambos lados y falta integrar FIFONAFE/migración 034/resumen ejecutivo mediante una etapa Git expresamente autorizada. No copiar el árbol local completo sobre dev.
