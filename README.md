# SSALFER (Sistema de Seguimiento de Actividades de Liberación Ferroviaria) (PA)

Sistema para organizar el desarrollo y las pruebas del proyecto de liberación
de derechos de vía.

## Arquitectura

El Compose base define tres servicios: `db`, `backend` y `pgadmin`.
El frontend oficial es `frontend-ssalfer/`: HTML/CSS/JavaScript estático servido
por Nginx. El cuarto servicio, `frontend_ssalfer`, se incorpora únicamente al
seleccionar explícitamente el overlay `docker-compose.ssalfer.yml` de la raíz:

| Servicio | Función | Puerto local predeterminado |
| --- | --- | --- |
| `frontend_ssalfer` (overlay) | SSALFER estático en Nginx, proxy `/api/` | `5174` |
| `backend` | API FastAPI y SQLAlchemy | `8000` |
| `db` | PostgreSQL 15 con PostGIS 3.3 | `5433` |
| `pgadmin` | Administración web de PostgreSQL | `5050` |

Los servicios se comunican por sus nombres DNS de Compose (`db`, `backend`).
`localhost` se usa únicamente desde la computadora anfitriona.

## Requisitos

Se necesita Docker con el plugin oficial de Compose. Comprueba la instalación:

```bash
docker version
docker compose version
```

En Windows existen dos alternativas válidas. La elección queda a consideración
de quien instala el entorno:

1. **Docker Desktop con backend WSL2.** Es la opción con interfaz gráfica y
   administración integrada. Debe habilitarse la integración con la
   distribución WSL que contiene el repositorio.
2. **Docker Engine instalado directamente dentro de WSL2, sin Docker
   Desktop.** Ofrece un flujo muy parecido a Linux nativo y menor integración
   gráfica. Requiere habilitar `systemd` en WSL2 e instalar Engine, Buildx y el
   plugin Compose desde el repositorio oficial de Docker.

No es necesario instalar ambas opciones. Si se usa Docker Engine dentro de
WSL2, todos los comandos Docker deben ejecutarse en la terminal de esa
distribución. Consulta las guías oficiales:

- [Docker Desktop para Windows](https://docs.docker.com/desktop/setup/install/windows-install/)
- [Docker Engine para Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- [Docker Engine después de la instalación](https://docs.docker.com/engine/install/linux-postinstall/)

En Linux nativo se recomienda Docker Engine. No se recomienda ejecutar Docker
permanentemente como `root`; agrega el usuario al grupo `docker` siguiendo la
guía oficial.

### Ubicación recomendada en WSL2

Clona el repositorio dentro del sistema de archivos Linux:

```bash
mkdir -p ~/proyectos
cd ~/proyectos
git clone <URL_DEL_REPOSITORIO>
cd Software-PA
```

Una ruta bajo `/home` ofrece mejor rendimiento para bind mounts, hot reload e
`inotify` que `/mnt/c`. Desde VS Code para Windows, instala la extensión WSL y
abre el proyecto desde Ubuntu con `code .`.

## Configuración

Solo para una instalación local nueva y aislada, desde la raíz del repositorio
y sin sobrescribir un archivo de entorno existente:

```bash
cp .env.example .env
```

Edita `.env` y reemplaza todos los valores que comienzan con `change_me`.
Genera `SECRET_KEY`, por ejemplo, con:

```bash
openssl rand -hex 32
```

El archivo `.env` contiene secretos, está ignorado por Git y no debe
confirmarse. Comprueba antes de iniciar:

```bash
docker compose --env-file .env -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.ssalfer.yml config --quiet
```

Compose detendrá la validación si falta una variable obligatoria.
El backend también rechazará `SECRET_KEY` que sigan siendo placeholders o sean
demasiado cortas.

Configura por separado `POSTGRES_ADMIN_USER`/`POSTGRES_ADMIN_PASSWORD` para
bootstrap y migraciones, y `DB_RUNTIME_USER`/`DB_RUNTIME_PASSWORD` para
FastAPI. El backend no recibe las credenciales owner. En un volumen existente,
recrear el contenedor sólo actualiza su entorno: no vuelve a ejecutar
`docker-entrypoint-initdb.d`. El Baseline V1 y la provisión posterior se
documentan en [docs/MIGRACIONES.md](docs/MIGRACIONES.md).

### Bootstrap del primer administrador

Antes de ejecutar `scripts/create_admin.py`, define valores propios del entorno
y expórtalos en la shell que ejecutará el comando:

```bash
ADMIN_EMAIL
ADMIN_NOMBRE
ADMIN_APELLIDO_PATERNO
ADMIN_APELLIDO_MATERNO
```

Estas variables no sensibles no se inyectan automáticamente al contenedor en
ejecución; pásalas al comando de bootstrap. La contraseña se captura por prompt
interactivo, sin eco:

El primer administrador es un bootstrap owner explícito. El servicio FastAPI
no cambia de identidad:

```bash
set -a; source .env; set +a
docker compose run --rm --no-deps \
  -e ADMIN_DATABASE_MODE=owner \
  -e POSTGRES_ADMIN_USER \
  -e POSTGRES_ADMIN_PASSWORD \
  -e ADMIN_EMAIL \
  -e ADMIN_NOMBRE \
  -e ADMIN_APELLIDO_PATERNO \
  -e ADMIN_APELLIDO_MATERNO \
  backend python scripts/create_admin.py
```

La contraseña debe tener al menos 12 caracteres e incluir mayúscula,
minúscula, número y símbolo. Para automatizaciones controladas puede pasarse
`ADMIN_PASSWORD` como variable temporal del proceso; no la dejes persistente en
archivos compartidos, historial de shell, logs ni capturas. El script rechaza
placeholders y no contiene una contraseña predeterminada.

## Desarrollo y QA aislado

Estos ejemplos de construcción, arranque y comprobación son exclusivamente para
un daemon/VM desechable previamente autorizado, con DB, uploads, red, puertos y
credenciales propios. No son instrucciones para patrenes ni para una base activa
del desarrollador. La fase de retiro local de React solo valida estáticamente;
no autoriza ejecutar los comandos de arranque de esta sección ni los de DB de
las secciones siguientes.

La opción preferida para QA funcional es una VM aislada donde residan tanto el
repositorio como su Docker Engine. Ejecutar Compose y las pruebas HTTP desde
esa misma VM, con todos los recursos de QA desechables dentro de ella.

Un Docker context remoto solo selecciona el daemon; no garantiza aislamiento de
rutas, bind mounts ni puertos. Los orígenes de los bind mounts deben existir en
el host del daemon, en las rutas que Compose resuelva; el contexto no transfiere
esos directorios. Los puertos publicados en `127.0.0.1` pertenecen al host del
daemon, no al equipo cliente. Ejecutar las comprobaciones HTTP desde una
ubicación con acceso al servicio: para esos puertos, desde el propio host del
daemon o mediante un acceso QA explícitamente autorizado y verificado. Un
`curl localhost` desde el cliente del contexto remoto no comprueba ese servicio.

Prepara un archivo `.env.qa` nuevo con valores sintéticos propios del entorno,
sin copiar secretos de un despliegue. `.env.qa` está excluido de Git por la regla
`.env.*` de `.gitignore`; comprobarlo con `git check-ignore -v -- .env.qa` antes
de preparar el archivo. Define `CORS_ORIGINS=http://localhost:5174`
y `SSALFER_HOST_PORT=5174`. `http://localhost:5174` y
`http://127.0.0.1:5174` son orígenes distintos: CORS/CSRF deben reflejar exactamente
la URL usada en el navegador (esquema, host y puerto), incluso detrás del proxy.
No se cambian cookies ni protecciones CSRF.

Se conservan deliberadamente dos fallbacks históricos `5173`: el de
`CORS_ORIGINS` del backend en `docker-compose.yml` y el de `backend/app/config.py`.
No son la configuración de SSALFER; proporciona `CORS_ORIGINS` explícitamente.

Dentro de la VM, en Bash/Zsh, verificar que `QA_DOCKER_CONTEXT` identifica el
contexto local de su Docker Engine exclusivo y usar siempre la misma selección
explícita. El nombre de proyecto por sí solo no
prueba aislamiento del daemon ni de los binds:

```bash
# QA_DOCKER_CONTEXT debe identificar el contexto local del Engine de la VM QA.
dcqa() {
  docker --context "${QA_DOCKER_CONTEXT:?Define el contexto QA exclusivo}" compose \
    --env-file .env.qa --project-name software-pa-qa \
    -f docker-compose.yml -f docker-compose.override.yml \
    -f docker-compose.ssalfer.yml "$@"
}
dcqa config --quiet
# Solo en ese entorno nuevo y autorizado: preparar db según MIGRACIONES.md.
dcqa up -d db
# Tras tener db saludable y los prerrequisitos de la instalación resueltos:
dcqa build backend frontend_ssalfer
dcqa up -d --no-deps backend
# Esperar a que backend esté saludable antes de iniciar Nginx.
dcqa up -d --no-deps frontend_ssalfer
# pgAdmin es opcional y se inicia por nombre, si hace falta.
dcqa ps
```

`docker-compose.override.yml` proporciona `--reload` y binds de backend,
incluido `./backend/uploads:/app/uploads`. El hot reload solo aplica al backend;
SSALFER se empaqueta como estáticos en Nginx, sin servidor Vite ni bind de fuentes.
Con `-f` explícitos, el override no se añade automáticamente: hay que enumerarlo.

Servicios locales (si se han iniciado en el QA autorizado):

- SSALFER: <http://localhost:5174/Index.html>
- API y documentación: <http://localhost:8000/docs>
- PgAdmin, si se inicia: <http://localhost:5050>
- PostgreSQL para herramientas locales: `localhost:5433`

Los puertos versionados se publican en `127.0.0.1`; cualquier cambio de puerto
QA requiere revisar también el origen exacto. El Nginx oficial reenvía `/api/`
a FastAPI; Live Server sin ese proxy no reproduce esta instalación.

## Selección sin bind mounts

La combinación declarativa de `docker-compose.yml`, `docker-compose.prod.yml`
y `docker-compose.ssalfer.yml` incluye SSALFER y conserva backend sin reload,
con `APP_ENV=production`, cookies `Secure` y `CORS_ORIGINS` HTTPS obligatorio.
No combinar `override` con `prod`. Validar esta selección con `config` no arranca
servicios. Su ejecución requiere QA HTTPS real compatible con cookies Secure;
el despliegue productivo y TLS quedan fuera de esta fase. Ver
[frontend-ssalfer/DEPLOY.md](frontend-ssalfer/DEPLOY.md).

## Base de datos, migraciones y datos iniciales

Una instalación vacía aplica directamente
`backend/db/migrations/001_baseline_v1.sql`. El baseline crea PostGIS, la
estructura base de tablas de dominio y soporte (52 tablas físicas iniciales),
constraints, funciones, triggers, índices, cuatro vistas de SOFTWARE-PA y
catálogos estructurales. No contiene `bien_afectado` ni columnas o
sincronizaciones exclusivamente legacy.

`backend/db/init/001_bootstrap_roles.sh` provisiona por variables de entorno
el rol `software_pa_app` y el LOGIN runtime. Después,
`backend/db/init/002_apply_migrations.sh` invoca el runner con checksum. Las
contraseñas no forman parte del SQL.

La secuencia exacta, las comprobaciones para bases existentes y los comandos de
respaldo están documentados en [docs/MIGRACIONES.md](docs/MIGRACIONES.md).

Resumen para una instalación nueva:

```bash
docker compose up -d --build db
set -a; source .env; set +a
# Crear primero el administrador con el bootstrap owner explícito anterior.
# El fixture territorial requiere un administrador activo para su auditoría.
# Cargar el catálogo territorial reproducible.
docker compose exec -T db sh -lc \
  'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f -' \
  < backend/db/fixtures/001_catalogo_territorial_inegi.sql
backend/scripts/utils/set_runtime_credentials.sh
docker compose up -d backend
curl --fail http://127.0.0.1:${BACKEND_HOST_PORT:-8000}/health
```

`schema_migrations` registra `001`, el nombre `baseline_v1` y el SHA-256
del archivo. Las migraciones nuevas comienzan en `002`; el runner rechaza una
migración aplicada si su archivo fue modificado.

### Catálogo nacional RAN en cada servidor

Git incluye el dataset aprobado en `backend/db/fixtures/catalogo_nucleos_ran.csv`,
su manifiesto de integridad y el crosswalk RAN→INEGI. Son **32,278 claves externas**;
no incluye los 51 registros sintéticos QA/GIS adicionales de la base de pruebas.
No hace falta copiar `software_pa_test`, copiar un CSV manualmente ni acceder a
`fuentes_locales/`. Las migraciones crean estructura; el importador sincroniza
este dataset maestro por separado. No existe una migración 029 para esta carga.

Prerrequisitos: DB destino explícita en la configuración, migraciones hasta 028,
administrador activo creado con el bootstrap existente y catálogo territorial
cargado **después** de ese administrador. En un volumen existente ejecutar el
runner oficial; el init de PostgreSQL no se repite. Ver
[MIGRACIONES](docs/MIGRACIONES.md) y [fixtures](backend/db/fixtures/README.md).

Después de actualizar el servidor, ejecutar desde la raíz del repositorio:

```bash
git pull --ff-only
# Valores reales propios de este servidor; DB_NAME en .env debe apuntar al destino.
TARGET_DATABASE="nombre_real_de_la_base"
IMPORT_ACTOR_EMAIL="correo_del_administrador_activo"
docker compose -f docker-compose.yml -f docker-compose.prod.yml build backend

# Siempre revisar el plan primero. No escribe en PostgreSQL.
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm --no-deps \
  backend bash scripts/sync_catalogo_ran.sh \
  --expected-database "$TARGET_DATABASE"

# Autorización explícita de la carga; resuelve el ID del actor en esta misma DB.
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm --no-deps \
  backend bash scripts/sync_catalogo_ran.sh \
  --expected-database "$TARGET_DATABASE" \
  --actor-email "$IMPORT_ACTOR_EMAIL" --apply

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps backend
curl --fail http://127.0.0.1:${BACKEND_HOST_PORT:-8000}/health
```

`/health` debe reportar schema 28. Después comprobar autenticado
`GET /api/catalogos/nucleos?limit=20` y un filtro territorial conocido; comparar
con SQL si es necesario. El endpoint conserva su autenticación y sus cuatro roles.
En desarrollo usar consistentemente la configuración Compose de desarrollo.

También puede ejecutarse directamente en un entorno Python con `psycopg2` y
conexión configurada mediante `DB_*` o `DATABASE_URL`:

```bash
./backend/scripts/sync_catalogo_ran.sh \
  --expected-database "$TARGET_DATABASE" \
  --actor-email "$IMPORT_ACTOR_EMAIL" --apply
```

El script verifica manifiesto, bytes, conteos, crosswalk y base real antes de
importar. Si `DATABASE_URL` contradice las variables `DB_*`, aborta. Sin `--apply`
sólo informa el plan. Con cero altas/cambios informa
`CATALOGO RAN YA SINCRONIZADO` y omite apply. Después de escribir exige otro dry-run
sin altas/cambios y verifica cobertura de todas las claves del CSV.
No borra registros adicionales ni reactiva bajas administrativas. Informa por
separado cobertura, claves activas del dataset y claves extra; el conteo global
de `nucleo_agrario` puede ser mayor que 32,278.

Los datos de prueba son opcionales y deben cargarse después del administrador:

```bash
SEED_OBJECTIVE_CONFIRM=1 docker compose exec \
  -e SEED_OBJECTIVE_CONFIRM backend python scripts/seed_objective_demo.py
```

Las credenciales no se documentan en el repositorio. PgAdmin y PostgreSQL usan
los valores definidos localmente en `.env`. `backend/db/seed.sql` ya no crea
usuarios; requiere que exista un administrador activo para registrar la
auditoría de los datos semilla.

La autenticación web usa una sesión opaca en cookie HttpOnly y protección
CSRF; el frontend no guarda credenciales en `localStorage` y el backend no
acepta bearer/JWT como mecanismo de aplicación. En producción define
`APP_ENV=production`, `AUTH_COOKIE_SECURE=true` y un `CORS_ORIGINS` HTTPS
exacto del ambiente.

### Pruebas backend autenticadas

La suite de backend necesita credenciales de un administrador activo en una
base aislada de pruebas. No uses credenciales productivas ni las guardes en el
repositorio:

```bash
export TEST_ADMIN_EMAIL="<admin_de_pruebas>"
export TEST_ADMIN_PASSWORD="<password_de_pruebas>"
docker compose exec \
  -e TEST_ADMIN_EMAIL="$TEST_ADMIN_EMAIL" \
  -e TEST_ADMIN_PASSWORD="$TEST_ADMIN_PASSWORD" \
  backend python -m pytest -v
```

Si la base de pruebas no tiene administrador, créalo primero con
`scripts/create_admin.py` usando valores propios del entorno. La contraseña
debe cumplir la política mínima y no puede ser un placeholder.

## Operación dirigida en QA aislado

Usar la función `dcqa` y el entorno exclusivo definidos arriba; estos comandos
no aplican a patrenes. Revisar estado y logs por servicio:

```bash
dcqa ps
dcqa logs --tail=100 backend frontend_ssalfer
# Tras cambiar los estáticos, reconstruir y recrear solo SSALFER:
dcqa build frontend_ssalfer
dcqa up -d --no-deps frontend_ssalfer
# Si se autoriza por separado actualizar backend en ese QA:
dcqa build backend
dcqa up -d --no-deps backend
```

Un `restart` no actualiza las variables con las que se creó un contenedor ni
reconstruye archivos empaquetados. No usar arranques/reconstrucciones generales,
limpieza de huérfanos o eliminación de volúmenes para este retiro. Quitar React
del código no retira un contenedor ya existente: su tratamiento en un servidor
requiere inventario y autorización independiente.

## Comprobaciones en QA aislado

Ejecutar desde la misma VM QA, solo con los puertos verificados del entorno
exclusivo (los siguientes ejemplos usan los valores predeterminados). Si se usa
un contexto remoto, respetar las condiciones de acceso HTTP indicadas arriba:

```bash
dcqa ps
dcqa logs --tail=100 backend frontend_ssalfer
curl --fail http://localhost:8000/health
curl --fail http://localhost:5174/health
curl --fail http://localhost:5174/Index.html
```

`/health` de Nginx solo devuelve un estado estático; no comprueba FastAPI ni DB.
El healthcheck de backend consulta su propio `/health`. SSALFER espera backend
saludable al iniciar, pero su overlay no define un healthcheck de contenedor.
Probar `/api/`, login, permisos y flujos en navegador es una comprobación aparte;
incluso un GET autenticado puede actualizar la actividad de sesión en DB.

## Documentación del proyecto

La documentación técnica y funcional canónica reside en el directorio [`docs/`](docs/README.md):

- [Índice y precedencia documental](docs/README.md)
- [Modelo funcional objetivo](docs/MODELO_FUNCIONAL.md)
- [Fuentes y cobertura Excel](docs/FUENTES_Y_COBERTURA_EXCEL.md)
- [Arquitectura del sistema](docs/ARQUITECTURA.md)
- [Diccionario de datos](docs/DICCIONARIO_DATOS.md)
- [Gestión de migraciones](docs/MIGRACIONES.md)
- [Contrato de API](docs/API.md)
- [Especificación OpenAPI 3.1.0](docs/openapi.json)

## Reglas de colaboración

- No trabajar directamente en la rama `main`.
- Crear una rama por tarea, por ejemplo `feature/nombre-tarea`.
- Usar commits descriptivos (`feat:`, `fix:`, `docs:`, entre otros).
- Mantener la documentación canónica en `docs/` sincronizada con el código.

## Autores

- Jonathan Ponce
- Alfredo Cruz
