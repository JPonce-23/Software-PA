# Suministro de la candidata SSALFER ec379a6

La candidata ec379a6 usa PostgreSQL r2, backend p3, frontend y TLS. La entrega
autorizada es la carpeta completa `release-remediacion-r2-ec379a6`, con sus cuatro
TAR, manifiestos y scripts. El responsable de la entrega coloca esa carpeta en
un espacio institucional de acceso restringido y comunica su ubicación a los
integrantes autorizados. El identificador de la entrega es el SHA-256 de
`SHA256SUMS`, registrado en esta revisión.

## Verificar e importar

Copia la carpeta completa desde el canal autorizado y abre una terminal Linux
o WSL con Python 3.11 o posterior y acceso al Docker Engine local **linux/amd64**
con almacén de imágenes containerd. Se validó la carga con Docker Engine
29.1.3. Para integrar desde el repositorio, usa Docker Compose 2.24.4 o
posterior y el checkout que incluye este cambio.

Desde la raíz del paquete copiado:

```bash
set -euo pipefail
SSALFER_SUMS_SHA256=f210f4e3c8db40090d65e6aeec3240d1d0f91f8ca87d590501f07c8b08f17baa
SSALFER_SOCKET=/var/run/docker.sock
printf '%s  SHA256SUMS\n' "$SSALFER_SUMS_SHA256" | sha256sum --strict -c -
sha256sum --strict -c SHA256SUMS
SSALFER_ENGINE_ID="$(docker --host "unix://$SSALFER_SOCKET" info --format '{{.ID}}')"
printf 'Docker Engine local: %s\n' "$SSALFER_ENGINE_ID"
python3 -B scripts/importar-candidata.py --sha256sums-sha256 "$SSALFER_SUMS_SHA256" \
  --load --socket "$SSALFER_SOCKET" --engine-id "$SSALFER_ENGINE_ID"
```

Usa el socket y el ID del Engine asignado para tu entorno. El importador
verifica las cuatro identidades OCI, aborta ante colisiones de etiquetas y
permite reintentar la carga de la misma entrega.

## Elegir archivos Compose

| Objetivo | Selección explícita, en orden |
| --- | --- |
| Integrar localmente las cuatro imágenes candidatas | En el checkout, `docker-compose.yml`, `docker-compose.ssalfer.yml`, `docker-compose.prod.yml`, `deploy/ssalfer-candidata/compose.offline.yml`. |
| Trabajar con código fuente y reconstrucciones | En el checkout, sigue el [README del repositorio](../../README.md). Ese entorno usa el Compose base, el override de desarrollo y SSALFER. PA5 corresponde a ese flujo histórico. |
| QA de la candidata en un laboratorio aislado | En el paquete, `compose/compose.produccion.yml` seguido de `compose/compose.ensayo.yml`. |
| Producción de la candidata | En el paquete, solo `compose/compose.produccion.yml`, siguiendo el runbook autorizado. |

### Integración local de la candidata

Desde la raíz del checkout, prepara un archivo privado a partir de
`.env.example`. Completa `POSTGRES_ADMIN_USER`, `POSTGRES_ADMIN_PASSWORD`,
`DB_RUNTIME_USER`, `DB_RUNTIME_PASSWORD` y `SECRET_KEY` con valores locales y
define `DB_NAME` para esta instancia. Define `PUBLIC_HOST` sin puerto, por ejemplo
`ssalfer-dev.test`, y resuélvelo a `127.0.0.1` en el cliente. Define
`SSALFER_DEV_TLS_CERT_DIR` con una ruta absoluta a los certificados locales.
Debe contener `live/ssalfer/fullchain.pem` y `live/ssalfer/privkey.pem` para ese
nombre. El cliente debe confiar en la CA local. Elige una subred sin
solapamientos en `PROD_INTERNAL_SUBNET`, con su rango dinámico y la IP del proxy
según la [guía TLS](../tls/README.md). El único ingreso es el proxy TLS en
`127.0.0.1:80` y `127.0.0.1:443`. Verifica que esos puertos estén libres.

Con `SSALFER_SOCKET` de la importación y `SSALFER_DEV_ENV` apuntando al archivo
privado, selecciona un proyecto nuevo. Guarda su nombre para operar esa misma
instancia más adelante.

```bash
set -euo pipefail
: "${SSALFER_SOCKET:?}" "${SSALFER_DEV_ENV:?}"
docker_local=(docker --host "unix://$SSALFER_SOCKET")
SSALFER_DEV_PROJECT="ssalfer-dev-ec379a6-$(python3 -c 'import secrets; print(secrets.token_hex(6))')"
printf 'Proyecto local: %s\n' "$SSALFER_DEV_PROJECT"
compose_dev=("${docker_local[@]}" compose --env-file "$SSALFER_DEV_ENV" -p "$SSALFER_DEV_PROJECT"
  -f docker-compose.yml -f docker-compose.ssalfer.yml -f docker-compose.prod.yml
  -f deploy/ssalfer-candidata/compose.offline.yml)

"${compose_dev[@]}" config --images
"${compose_dev[@]}" config --quiet
existing_containers="$("${docker_local[@]}" ps -aq --filter "label=com.docker.compose.project=$SSALFER_DEV_PROJECT")"
existing_volumes="$("${docker_local[@]}" volume ls -q --filter "name=^${SSALFER_DEV_PROJECT}_")"
existing_networks="$("${docker_local[@]}" network ls -q --filter "name=^${SSALFER_DEV_PROJECT}_")"
test -z "$existing_containers$existing_volumes$existing_networks"
"${compose_dev[@]}" up -d --no-build --pull never --no-recreate
```

La configuración muestra cuatro referencias fijadas por digest. El arranque
crea volúmenes propios del proyecto y el volumen nuevo de PostgreSQL se
inicializa con los scripts del checkout. El proxy monta los certificados
locales en solo lectura.

### QA y producción de la candidata

Ejecuta Compose desde la raíz del paquete. Prepara el archivo de parámetros a
partir de `compose/parametros.example`. Asigna nombres exclusivos a los cuatro
volúmenes del destino.

- **QA.** Usa un Engine de laboratorio independiente, un proyecto nuevo,
  cuatro volúmenes nuevos, datos sintéticos y certificado de laboratorio.
  Sigue `runbooks/Laboratorio-OCI.md` del paquete para la preparación. La
  selección de QA aísla ambas redes y elimina los puertos publicados.
- **Producción.** Usa el proyecto y los volúmenes nuevos preparados en la
  ventana autorizada. Sigue `runbooks/Patrenes-ec379a6.md` del paquete para
  restauración, certificados, preflight y corte. El Compose lee el
  almacenamiento restaurado y publica el ingreso TLS en la interfaz
  expresamente configurada.

Para revisar solo el modelo, ejecuta `scripts/preflight.py` con el
`--env-file` del destino y `--solo-config`. Añade `--ensayo` para QA.

#### Arranque de QA

Con los volúmenes sintéticos preparados y el proyecto nuevo de QA:

```bash
set -euo pipefail
: "${SSALFER_QA_ENV:?}" "${SSALFER_QA_PROJECT:?}" "${SSALFER_SOCKET:?}" "${SSALFER_ENGINE_ID:?}"
python3 -B scripts/preflight.py --env-file "$SSALFER_QA_ENV" --ensayo \
  --socket "$SSALFER_SOCKET" --engine-id "$SSALFER_ENGINE_ID"
docker --host "unix://$SSALFER_SOCKET" compose --env-file "$SSALFER_QA_ENV" \
  -p "$SSALFER_QA_PROJECT" -f compose/compose.produccion.yml -f compose/compose.ensayo.yml \
  up -d --no-build --pull never --no-recreate --wait
```

#### Arranque de producción

Con los volúmenes del destino preparados y el proyecto nuevo de la ventana:

```bash
set -euo pipefail
: "${SSALFER_PROD_ENV:?}" "${SSALFER_PROD_PROJECT:?}" "${SSALFER_SOCKET:?}" "${SSALFER_ENGINE_ID:?}"
python3 -B scripts/preflight.py --env-file "$SSALFER_PROD_ENV" \
  --socket "$SSALFER_SOCKET" --engine-id "$SSALFER_ENGINE_ID"
docker --host "unix://$SSALFER_SOCKET" compose --env-file "$SSALFER_PROD_ENV" \
  -p "$SSALFER_PROD_PROJECT" -f compose/compose.produccion.yml \
  up -d --no-build --pull never --no-recreate --wait
```

## Evolución a un registro compartido

Cuando la organización apruebe el registro privado GHCR y su acceso, publicar
los cuatro artefactos congelados y verificar desde un Engine independiente
los manifiestos, la plataforma, la configuración y las capas recuperadas.
Proponer la adopción de las cuatro referencias remotas fijadas por digest en
una única revisión. La descarga se hará de forma explícita antes del
arranque. Hasta esa adopción, el paquete offline es la entrega oficial de la
candidata. Su copia se conserva como evidencia y para recuperación autorizada.

El [PR #9](https://github.com/JPonce-23/Software-PA/pull/9) describe una
publicación de PA5. Conservar su historial, catálogo y verificadores como
evidencia de PA5. El equipo debe resolver ese PR por separado y mantener
inactivo su workflow para el suministro de la candidata ec379a6.
