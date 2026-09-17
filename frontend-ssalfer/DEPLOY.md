# Despliegue del frontend SSALFER con Docker Desktop

Esta guía asume que usas **Docker Desktop** (la app de escritorio) y
que prefieres evitar la terminal en lo posible. Te aviso desde ya lo
más honesto: Docker Desktop es excelente para *ver y administrar*
contenedores (logs, reinicios, apagar/prender) desde su interfaz
gráfica, pero para *construir imágenes nuevas* (lo que necesitamos
aquí, porque el frontend SSALFER es una imagen nueva que no existe
todavía) no tiene un botón de "construir desde una carpeta" en todas
las versiones — así que hay **un único comando** que sí tendrás que
pegar en una terminal. Después de ese paso, todo lo demás (arrancar,
detener, ver logs, reconstruir) lo puedes hacer con clics desde
Docker Desktop sin volver a tocar la terminal.

Hay dos escenarios distintos. Empieza por el primero.


## Parte 1 — Conectar en LOCAL (para probar en tu máquina)

En desarrollo, backend y frontend pueden vivir en orígenes distintos
(`localhost:8000` y el puerto que uses para el frontend) sin
problema, porque en modo desarrollo las cookies de sesión usan
`AUTH_COOKIE_SAMESITE=lax` y `AUTH_COOKIE_SECURE=false` (los valores
por defecto de tu `.env`), y los navegadores tratan los distintos
puertos de `localhost` como el mismo "sitio". **No necesitas nginx
ni el `docker-compose.ssalfer.yml` todavía para esto.**

### Paso 1 — Backend corriendo

Si ya tienes el stack del backend levantado (`db` + `backend`) desde
Docker Desktop, continúa. Si no:

1. Abre Docker Desktop.
2. Ve a la pestaña **Containers**. Si ves un grupo llamado como tu
   proyecto (por el nombre de la carpeta del repo) con `db` y
   `backend` corriendo (círculo verde), ya está listo.
3. Si no existe ese grupo todavía, es la primera vez — necesitas el
   comando `docker compose up -d --build` una sola vez desde la
   carpeta del backend (pídele el `.env` ya configurado a tu equipo
   si no lo tienes, con `SECRET_KEY`, `POSTGRES_ADMIN_PASSWORD`, etc.
   — son los valores marcados `change_me` en `.env.example`).

### Paso 2 — Permitir el origen del frontend en CORS

Abre el archivo `.env` del backend (la carpeta donde está
`docker-compose.yml`) y ubica la línea:

```
CORS_ORIGINS=http://localhost:5173
```

Cámbiala (o agrega, separado por comas si el backend lo soporta —
si no, dale el valor exacto) por el puerto donde vas a servir el
frontend SSALFER en tu máquina. Por ejemplo, si lo vas a servir en
el puerto `5500`:

```
CORS_ORIGINS=http://localhost:5500
```

Después, en Docker Desktop, ve a **Containers → tu proyecto →
backend** y dale a **Restart** (ícono de flecha circular) para que
tome la variable nueva. No hace falta reconstruir la imagen, solo
reiniciar el contenedor.

### Paso 3 — Servir el frontend SSALFER localmente

La forma más simple sin usar la terminal: si usas VS Code, instala
la extensión **"Live Server"** y dale clic derecho a `Index.html` →
**"Open with Live Server"**. Anota el puerto que use (normalmente
`5500`) y asegúrate de que coincida con el que pusiste en
`CORS_ORIGINS` en el paso 2.

Si prefieres usar Docker Desktop para esto también:

1. Ve a la pestaña **Images** → botón **Pull** (o el buscador de
   arriba) → busca `nginx:alpine` → **Pull**.
2. Cuando termine, en la lista de imágenes da clic en `nginx:alpine`
   y luego en **Run**.
3. En el diálogo que aparece, abre **Optional settings** y llena:
   - **Container name**: `ssalfer-local`
   - **Ports** → Host port: `5500`, Container port: `80`
   - **Volumes** → Host path: la carpeta donde descomprimiste este
     entregable (la que contiene `Index.html`); Container path:
     `/usr/share/nginx/html`
4. Dale **Run**. Abre `http://localhost:5500` en el navegador.

Con esto, `config.js` usará su valor por defecto
(`http://localhost:8000/api`) porque `env.js` no define nada — no
necesitas tocar `env.js` para este escenario local.

### Verificar que sí quedó conectado

Abre `http://localhost:5500/Index.html`, inicia sesión con un
usuario real del backend y confirma que `dashboard.html` te muestre
proyectos reales (no "Cargando proyectos…" indefinidamente). Si ves
un error de CORS en la consola del navegador (F12 → Console), casi
siempre es porque `CORS_ORIGINS` no coincide EXACTAMENTE con el
origen del frontend (incluyendo el puerto).


## Parte 2 — Deploy real (mismo origen, con nginx y Docker Desktop)

Para producción SÍ es obligatorio que frontend y backend compartan
el mismo origen (mismo dominio y puerto tal como lo ve el
navegador), porque las cookies de sesión en producción usan el
prefijo `__Host-` (`__Host-pa_session`, `__Host-pa_csrf`), que el
navegador solo acepta si viajan por HTTPS y bajo el dominio exacto
que las emitió. Este entregable ya incluye todo lo necesario para
que un solo contenedor de nginx sirva el frontend Y reenvíe `/api/`
al backend, para que el navegador solo vea un origen.

### Paso 1 — Acomodar las carpetas

En la máquina donde vas a desplegar (o en tu repo, para subirlo a
control de versiones), deja esta estructura junto al backend:

```
Software-PA-feature-backend-logica/
  docker-compose.yml           <- del backend, tal cual está, sin tocar
  backend/                     <- del backend, sin tocar
  frontend-ssalfer/            <- todo el contenido de este entregable
    Index.html
    dashboard.html
    js/
    styles/
    img/
    pages/
    deploy/
      Dockerfile
      nginx.conf
      docker-compose.ssalfer.yml
```

Mueve `docker-compose.ssalfer.yml` de `frontend-ssalfer/deploy/` a
la raíz del repo (al mismo nivel que el `docker-compose.yml` del
backend) — ábrelo con un editor de texto primero si quieres
confirmar las rutas, están comentadas ahí mismo.

### Paso 2 — Variables de entorno de producción

En el `.env` que use el backend en el servidor de producción,
confirma o agrega:

```
APP_ENV=production
AUTH_COOKIE_SECURE=true
CORS_ORIGINS=https://<el-dominio-público-real>
SSALFER_HOST_PORT=5174
```

`CORS_ORIGINS` en este esquema no es estrictamente necesario para
que las cookies funcionen (el navegador solo habla con nginx, nunca
directo con el backend), pero déjalo correcto de todas formas como
buena práctica y por si algo llega a llamar al backend directo.

`https://<el-dominio-público-real>` debe ser el dominio final desde
el que la gente va a entrar (p. ej. `https://ssalfer.pa.gob.mx`).
Ese dominio también es el que debe apuntar (DNS / balanceador /
reverse proxy institucional de PA) al puerto `SSALFER_HOST_PORT`
(`5174` por defecto) del servidor donde corra este contenedor — la
gestión de HTTPS/certificado normalmente la resuelve un proxy
institucional delante de este contenedor (o puedes agregar Traefik/
Certbot si el servidor no tiene uno ya).

### Paso 3 — El único comando

Abre una terminal (en Windows: busca "PowerShell" o "Símbolo del
sistema" en el menú de inicio; en Mac: "Terminal") **en la carpeta
raíz del repo** (donde está `docker-compose.yml`) y pega:

```
docker compose -f docker-compose.yml -f docker-compose.ssalfer.yml up -d --build
```

Esto:
- No modifica nada del backend (usa su `docker-compose.yml` tal cual).
- Construye la imagen nueva de `frontend_ssalfer` a partir del
  `Dockerfile` que incluimos.
- Levanta el contenedor ya conectado a la misma red que `backend`.

### Paso 4 — Todo lo demás, desde Docker Desktop

A partir de aquí ya no necesitas la terminal:

- Abre Docker Desktop → pestaña **Containers**. Verás el grupo del
  proyecto con `db`, `backend`, `pgadmin`, `frontend` (el React
  existente) y el nuevo `frontend_ssalfer`.
- Clic en `frontend_ssalfer` → pestaña **Logs** para ver si nginx
  arrancó bien (debe decir algo como "start worker process").
- Para reiniciarlo tras algún cambio de configuración: botón
  **Restart** en esa misma fila.
- Para volver a construir después de que te entreguemos una
  actualización del frontend: sí tendrías que repetir el comando del
  Paso 3 una vez más (Docker Desktop no reconstruye solo cuando
  cambian archivos, a menos que actives "Watch" en Docker Desktop
  4.x+, que si quieres te explico aparte).

### Verificar

1. Entra a `http://localhost:5174` (o al dominio público una vez
   que el proxy institucional esté enfrente) → deberías ver el login
   de SSALFER.
2. Inicia sesión. Si el dashboard carga proyectos reales, la cookie
   de sesión y el proxy `/api/` están funcionando.
3. Revisa en el navegador (F12 → Application/Storage → Cookies) que
   la cookie de sesión aparezca bajo el MISMO origen que la URL de
   la barra de direcciones — si aparece un dominio distinto, algo en
   el proxy institucional está rompiendo el mismo-origen.


## Resumen de qué toca cada quién

| Qué | Dónde vive | ¿Se modificó el backend? |
|---|---|---|
| `window.SSALFER_API_URL` | `frontend-ssalfer/js/env.js` | No |
| `CORS_ORIGINS`, `AUTH_COOKIE_SECURE` | `.env` del backend (variables, no código) | No se tocó código, solo config por variables de entorno que ya existían |
| Proxy `/api/` → backend | `frontend-ssalfer/deploy/nginx.conf` (nuevo) | No |
| Nuevo servicio de Docker | `docker-compose.ssalfer.yml` (nuevo, archivo aparte) | No — el `docker-compose.yml` original queda intacto |
