# SSALFER — instalación y QA aislado

El frontend oficial vive en `frontend-ssalfer/` y contiene HTML, CSS y JavaScript
estáticos. Nginx sirve `Index.html`, páginas y recursos locales, y reenvía
`/api/` a `http://backend:8000/api/`. No necesita React ni Vite.

Esta fase retira React únicamente del repositorio local. No autoriza despliegue,
TLS, cambios en servicios existentes ni intervenciones sobre patrenes. Las
instrucciones de arranque de abajo requieren antes un daemon/VM exclusivo
expresamente autorizado, DB, uploads, red, puertos y credenciales desechables.
No usar la base activa del desarrollador ni destinos HTTP reales para QA.

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

## Estructura y configuración del cliente

El overlay `docker-compose.ssalfer.yml` ya está en la **raíz del repositorio**,
al mismo nivel que `docker-compose.yml`, `backend/` y `frontend-ssalfer/`.
No hay que moverlo desde `deploy/`. El Compose base define `db`, `pgadmin` y
`backend`; el overlay añade el cuarto servicio, `frontend_ssalfer`.

`js/env.js` se carga antes de `config.js` y ya asigna:

```js
window.SSALFER_API_URL = "/api";
```

La URL relativa utiliza el proxy del Nginx oficial. Live Server o un Nginx
genérico sin esa configuración no reenvían `/api/` a FastAPI y no reproducen
este flujo. Las variables del contenedor no reescriben automáticamente el JS
empaquetado; los cambios en estáticos requieren reconstrucción dirigida.

## Origen, cookies y CSRF

Para QA HTTP de desarrollo, un archivo `.env.qa` nuevo y exclusivo debe definir
`APP_ENV=development`, `AUTH_COOKIE_SECURE=false`,
`CORS_ORIGINS=http://localhost:5174` y `SSALFER_HOST_PORT=5174`, además de las
variables obligatorias de DB y autenticación con valores propios desechables.
No sobrescribir `.env`, `.env.deploy-mq` ni reutilizar credenciales productivas.
`.env.qa` está excluido de Git por la regla `.env.*` de `.gitignore`; comprobarlo
con `git check-ignore -v -- .env.qa` antes de preparar el archivo.

`http://localhost:5174` no equivale a `http://127.0.0.1:5174`: esquema, host y
puerto forman el origen. Configurar el origen exacto de la URL del navegador.
El proxy del mismo origen no elimina las validaciones CSRF del backend: el
login exige origen permitido y las peticiones mutables con sesión deben cumplir
la validación de origen, cookie y cabecera `X-CSRF-Token`. No desactivar estas
protecciones para resolver errores de configuración.

Se conservan como excepción mínima los fallbacks `http://localhost:5173` en
`docker-compose.yml` y `backend/app/config.py`. Para SSALFER, definir siempre
`CORS_ORIGINS` explícitamente; no depender de esos fallbacks.

## Selecciones declarativas, sin arranque

Usar todos los archivos explícitamente evita cargar un override accidental:

| Selección de archivos raíz | Servicios | Backend / uploads |
| --- | --- | --- |
| base | db, pgadmin, backend | Sin reload / volumen nombrado |
| base + override | Los tres | Reload / bind `./backend/uploads` |
| base + ssalfer | Los tres + frontend_ssalfer | Sin reload / volumen nombrado |
| base + override + ssalfer | Los cuatro | Reload / bind `./backend/uploads` |
| base + prod + ssalfer | Los cuatro | Producción, Secure / volumen nombrado |

`base`, `override`, `prod` y `ssalfer` corresponden a `docker-compose.yml`,
`docker-compose.override.yml`, `docker-compose.prod.yml` y
`docker-compose.ssalfer.yml`. No combinar desarrollo (`override`) con `prod`.
`config --quiet` y `config --services` validan la selección sin arrancar nada;
usar un entorno sintético y no volcar configuraciones con secretos.

Ejemplo solo declarativo con un archivo QA sin secretos:

```bash
docker compose --env-file .env.qa -f docker-compose.yml \
  -f docker-compose.override.yml -f docker-compose.ssalfer.yml config --quiet
docker compose --env-file .env.qa -f docker-compose.yml \
  -f docker-compose.override.yml -f docker-compose.ssalfer.yml config --services
```

## Instalación y actualización dirigida, solo tras autorizar infraestructura QA

Seguir los prerrequisitos de una instalación nueva del [README](../README.md)
y [MIGRACIONES](../docs/MIGRACIONES.md) únicamente en el entorno desechable.
Dentro de la VM, verificar que `QA_DOCKER_CONTEXT` identifica el contexto local
de su Docker Engine exclusivo antes de ejecutar estos ejemplos Bash/Zsh:

```bash
# QA_DOCKER_CONTEXT debe identificar el contexto local del Engine de la VM QA.
dcqa() {
  docker --context "${QA_DOCKER_CONTEXT:?Define el contexto QA exclusivo}" compose \
    --env-file .env.qa --project-name software-pa-qa \
    -f docker-compose.yml -f docker-compose.override.yml \
    -f docker-compose.ssalfer.yml "$@"
}
dcqa config --quiet
# Solo para la instalación QA nueva y autorizada:
dcqa up -d db
# Tras preparar DB y resolver los prerrequisitos del backend:
dcqa build backend frontend_ssalfer
dcqa up -d --no-deps backend
# Esperar backend saludable; luego iniciar SSALFER por nombre:
dcqa up -d --no-deps frontend_ssalfer
dcqa ps
dcqa logs --tail=100 backend frontend_ssalfer
```

Para actualizar únicamente estáticos en ese QA autorizado:

```bash
dcqa build frontend_ssalfer
dcqa up -d --no-deps frontend_ssalfer
```

El botón Restart no actualiza variables de creación. Cambios de entorno del
backend requieren recrear específicamente backend, con revisión y autorización
del entorno afectado; un cambio de JS empaquetado requiere reconstruir SSALFER.
No ejecutar un `up --build` general para esta limpieza ni asumir que un proyecto
Compose compartido corresponde a un único checkout. El diff no elimina ni
reconfigura contenedores React existentes ni su política de reinicio.

## QA funcional pendiente de entorno exclusivo

Ejecutar las pruebas HTTP desde la misma VM QA. Si se usa un contexto remoto,
respetar las condiciones de acceso HTTP indicadas al inicio de esta guía.
Usar la URL QA verificada (predeterminada `http://localhost:5174/Index.html`)
y cuentas desechables de cada rol. Login y cualquier petición autenticada pueden
escribir sesiones/actividad, incluso mediante GET. Revisar individualmente los
scripts de `deploy/`: no ejecutar sus 37 QA indiscriminadamente.

- Acceso a `Index.html`, rutas HTML directas, estáticos y 404.
- Login, sesión, logout, expiración y CSRF; origen permitido y rechazado.
- Roles, permisos por proyecto y rutas administrativas.
- Dashboard, GIS/mapas, expedientes, documentos y descargas.
- CSV/XLSX y reportes, verificando contenido y permisos.
- Proxy `/api/` a FastAPI. Comparar `/health` de backend con `/health` de Nginx:
  este último solo devuelve `ok` estático y no acredita salud de DB/API.

El overlay no define un healthcheck de contenedor para SSALFER; su dependencia
exige backend saludable al inicio. No presentar el health estático como prueba
integral ni los tests Node con dobles como certificación de navegador/API.

## Operación real y producción fuera de esta fase

La selección base + prod + ssalfer conserva `APP_ENV=production`,
`AUTH_COOKIE_SECURE=true` y un origen HTTPS explícito obligatorio. Su validación
estática no autoriza arrancarla: requiere QA HTTPS real compatible con cookies
Secure y revisión de la cadena de proxies. TLS y despliegue productivo requieren
un procedimiento y autorización separados; aquí no se prescribe su ejecución.

Los antecedentes de patrenes (proyecto compartido entre checkouts, montajes de
backend/uploads y publicación local no versionada en puerto 80) requieren un
inventario operativo aparte antes de cualquier recreación. No se corrigen con
este retiro local, que tampoco interviene en Control Vehicular.
