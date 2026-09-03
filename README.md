# SSALFER (Sistema de Seguimiento de Actividades de Liberación Ferroviaria) (PA)

Sistema para organizar el desarrollo y las pruebas del proyecto de liberación
de derechos de vía.

## Arquitectura

El entorno se ejecuta con Docker Compose y contiene cinco servicios:

| Servicio | Función | Puerto local predeterminado |
| --- | --- | --- |
| `frontend` | React 19 y Vite; Nginx en modo producción | `5173` |
| `backend` | API FastAPI y SQLAlchemy | `8000` |
| `alertas_scheduler` | Generación periódica de alertas ORV | No publica puerto |
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

Desde la raíz del repositorio:

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
docker compose config --quiet
```

Compose detendrá la validación si falta una variable obligatoria.
El backend también rechazará `SECRET_KEY` que sigan siendo placeholders o sean
demasiado cortas.

Configura por separado `POSTGRES_ADMIN_USER`/`POSTGRES_ADMIN_PASSWORD` para
bootstrap y migraciones, y `DB_RUNTIME_USER`/`DB_RUNTIME_PASSWORD` para
FastAPI. El backend no recibe las credenciales owner. En un volumen existente,
recrear el contenedor sólo actualiza su entorno: no vuelve a ejecutar
`docker-entrypoint-initdb.d`. El Baseline V1 y la provisión posterior se
documentan en [docs/migraciones.md](docs/migraciones.md).

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

## Desarrollo

`docker-compose.override.yml` se carga automáticamente. Mantiene los bind
mounts y el hot reload del backend y frontend:

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f
```

Servicios disponibles:

- Frontend: <http://localhost:5173>
- API y documentación: <http://localhost:8000/docs>
- PgAdmin: <http://localhost:5050>
- PostgreSQL para herramientas locales: `localhost:5433`

Los puertos se publican únicamente en `127.0.0.1`. Pueden cambiarse en `.env`.

## Ejecución sin bind mounts

La configuración `docker-compose.prod.yml` construye un frontend estático con
Nginx y ejecuta el backend sin hot reload:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Esta variante es útil para validar imágenes inmutables. Antes de un despliegue
expuesto a Internet todavía deben definirse TLS, gestión externa de secretos,
respaldos y una política de publicación de puertos.

Para detener esta variante usa los mismos archivos:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
```

## Base de datos, migraciones y datos iniciales

Una instalación vacía aplica directamente
`backend/db/migrations/001_baseline_v1.sql`. El baseline crea PostGIS, 51
tablas funcionales, constraints, funciones, triggers, índices, cuatro vistas
de SOFTWARE-PA y catálogos estructurales. No contiene `bien_afectado` ni
columnas o sincronizaciones exclusivamente legacy.

`backend/db/init/001_bootstrap_roles.sh` provisiona por variables de entorno
el rol `software_pa_app` y el LOGIN runtime. Después,
`backend/db/init/002_apply_migrations.sh` invoca el runner con checksum. Las
contraseñas no forman parte del SQL.

La secuencia exacta, las comprobaciones para bases existentes y los comandos de
respaldo están documentados en [docs/migraciones.md](docs/migraciones.md).

Resumen para una instalación nueva:

```bash
docker compose up -d --build db
set -a; source .env; set +a
# Cargar el catálogo territorial reproducible.
docker compose exec -T db sh -lc \
  'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f -' \
  < backend/db/fixtures/001_catalogo_territorial_inegi.sql
# Crear el primer administrador con el bootstrap owner explícito anterior.
backend/scripts/utils/set_runtime_credentials.sh
docker compose up -d backend
curl --fail http://127.0.0.1:${BACKEND_HOST_PORT:-8000}/health
```

`schema_migrations` registra `001`, el nombre `baseline_v1` y el SHA-256
del archivo. Las migraciones nuevas comienzan en `002`; el runner rechaza una
migración aplicada si su archivo fue modificado.

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

## Operación diaria

```bash
# Iniciar o actualizar servicios
docker compose up -d

# Estado y salud
docker compose ps

# Logs de todos los servicios o de uno
docker compose logs -f
docker compose logs -f backend

# Reconstruir únicamente backend y scheduler, que comparten imagen
docker compose build backend alertas_scheduler
docker compose up -d backend alertas_scheduler

# Reconstruir únicamente frontend
docker compose up -d --build frontend

# Detener sin eliminar contenedores ni datos
docker compose stop

# Eliminar contenedores y red, conservando volúmenes
docker compose down
```

Advertencia: el siguiente comando elimina los volúmenes de PostgreSQL y
PgAdmin. Supone pérdida de datos y configuraciones persistentes:

```bash
docker compose down -v
```

## Validación rápida

```bash
docker compose ps
docker compose logs --tail=100 db backend alertas_scheduler frontend pgadmin
curl --fail http://localhost:8000/
curl --fail http://localhost:5173/
docker compose exec db sh -lc \
  'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
docker compose exec frontend \
  node -e "fetch('http://backend:8000/').then(r=>{console.log(r.status);process.exit(r.ok?0:1)})"
```

Todos los servicios deben aparecer activos y saludables, sin reinicios
constantes.

## Reglas de colaboración

- No trabajar directamente en la rama `main`.
- Crear una rama por tarea, por ejemplo `feature/nombre-tarea`.
- Usar commits descriptivos (`feat:`, `fix:`, `docs:`, entre otros).
- Documentar en `docs/` las decisiones importantes de arquitectura.

## Autores

- Jonathan Ponce
- Alfredo Cruz
