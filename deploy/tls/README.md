# Entrada HTTPS de SSALFER

Selección explícita: `docker-compose.yml`, `docker-compose.ssalfer.yml`,
`docker-compose.prod.yml`, en ese orden. Requiere Docker Compose >= 2.24.4
para `!reset`; no combinar con `docker-compose.override.yml`.
Validar primero con `config --quiet`, sin volcar secretos. Esta configuración
no autoriza iniciar ni cambiar servicios institucionales.

`PUBLIC_HOST` es un dominio/IPv4 sin esquema, puerto ni ruta. El único origen
productivo es `https://PUBLIC_HOST` en 443. Elegir `PROD_INTERNAL_SUBNET` sin
solapamientos, `PROD_INTERNAL_DYNAMIC_RANGE` como subconjunto para asignación
dinámica y `TLS_PROXY_IP` dentro de la subred, fuera de ese rango dinámico. Ese peer exacto es la única IP
confiable para atribución SS-04; el edge sustituye XFF entrante. No colocar
otro balanceador delante sin revisar esa atribución y el límite por IP.

Sólo el edge publica 80/443. DB, backend y SSALFER no publican puertos;
pgAdmin queda en el perfil `admin-tools`, también sin puertos. La red de datos
es interna. No usar `--service-ports` ni agregar publicaciones para QA real.

El volumen `tls_certificates` debe contener
`live/ssalfer/fullchain.pem` y `live/ssalfer/privkey.pem`, con lectura exclusiva
del administrador/proxy. Sin certificado el edge falla cerrado. Proveer cadena
válida, DNS, firewall y un gestor de renovación externo. El challenge HTTP-01
puede escribirse en `acme_challenges`; el resto de HTTP redirige con 308.
Después de renovar, validar `nginx -t` y recargar únicamente el edge. No se
instala un bucle de certbot ni se solicita un certificado durante el arranque.
HSTS se envía sólo sobre HTTPS; comprobar certificados antes de habilitar el
acceso público. Un certificado de laboratorio no acredita confianza pública.

Se conserva CSP Report-Only de PR6 (incluye frames/blob usados por bibliotecas),
sin activar CSP bloqueante sin QA de navegador. Nosniff, no-referrer,
SAMEORIGIN, permisos y no-store son canónicos en éxitos y errores. Cookies
__Host- Secure/HttpOnly de sesión, CSRF y CORS estricto siguen en FastAPI.
La documentación OpenAPI permanece deshabilitada y el edge la deniega.
Los logs de acceso de ambos Nginx sólo incluyen metadatos generados; los logs
de error nativos requieren recolección protegida, revisión y retención propia.

## Contrato HTTP

| Ruta normalizada | Máximo de cuerpo | Máximo de archivo |
| --- | --- | --- |
| POST /api/auth/sesiones | 16 KiB | no aplica |
| /api/documentos/{id}/versiones | 26 MiB | 25 MiB = 26 214 400 bytes |
| /api/proyectos/{id}/importaciones | 101 MiB | 100 MiB |
| /api/proyectos/{id}/geoespacial/{ddv,nucleos,parcelas}/importaciones | 101 MiB | 100 MiB |
| Resto, incluidos recursos estáticos | 1 MiB | no aplica |

Los dos proxies evitan cerrar el upstream antes de terminar de enviar un cuerpo
rechazado tempranamente (por ejemplo 401), conservando su estado HTTP.
Los dos proxies mantienen los límites por ruta, con y sin slash final. Un MiB
son 1 048 576 bytes. El margen de 1 MiB es para multipart: un archivo en el
máximo con metadatos normales cabe; el cuerpo completo sigue limitado. El
backend comprueba el archivo incluso si cabe en el proxy. Producción fija los
límites funcionales para coincidir con la interfaz. Cambiarlos exige revisar
API, interfaz, ambos proxies y sus pruebas. El valor antiguo «20 MB» de la
interfaz y el fallback de 20 MiB se sustituyen por el contrato de 25 MiB ya
declarado en Compose/.env.example; no se cambia la lista de formatos admitidos.
SSALFER conserva los mensajes específicos JSON y la traducción de HTML 413/429.

El limitador de login es compartido entre workers Nginx: 5 peticiones/minuto
sostenidas por IP, seis inmediatas (una más burst=5), 429 al exceder. Sólo POST
login consume cuota; el bloqueo de cuenta en PostgreSQL sigue vigente. Una
zona sólo cubre una instancia edge; NAT de oficinas y múltiples edges requieren
calibración y, si corresponde, un limitador distribuido. El edge espera hasta
300 s al upstream para GIS; los presupuestos internos GDAL siguen aplicándose.

## UID 10001 y SS-12

La imagen crea uploads nuevos como 10001:10001/0700 y mantiene el código como
root, legible sin escritura. Nunca hace chown/chmod recursivo sobre un volumen.
Antes de cambiar UID en un volumen existente: detener todos sus escritores y
recuperadores, respaldar juntos DB/archivos, inventariar propietarios/permisos
y comprobar el acceso como 10001 con `python scripts/check_upload_access.py`.
El preflight es de sólo metadatos, no repara ni lee contenidos; devuelve códigos
y conteos. Los directorios de documentos/GIS deben permitir escritura a 10001;
los históricos deben ser legibles, sin abrirlos al público. Aplicar, con revisión
operativa, sólo cambios de propietario/modo de las entradas exactas necesarias.
No usar chmod 777, chown global, ni ACL de escritura para grupos generales.

`.ss12-writers` requiere propietario 10001 y modo 0700; cada lock permanente
requiere 10001/0600, cero bytes y un solo enlace. Ajustar propietario **en el
mismo inode** cuando corresponda. No eliminar, copiar ni recrear locks, staging,
publicados o raíz: 032 registra device/inode de raíz/directorio/lock. Tras una
restauración/cambio de filesystem esa identidad puede invalidarse; requiere
revisión SS-12, nunca adoptar automáticamente archivos antiguos como recuperables.
Los históricos sin coordinación siguen siendo descargables, sin asignarles
pruebas de recuperación que no tienen. No se modifican migraciones 031/032.

## Capacidad

Dos workers Uvicorn, sin reload; se mantienen `--no-proxy-headers`,
`--no-access-log` y logging.json. Pools por proceso: 5 + 2, espera 10 s;
techo predeterminado API 14 conexiones. Reservar conexiones de operación/migración
y multiplicar por réplicas si se agregan. PostgreSQL tiene 60 conexiones,
shared_buffers 128 MiB, work_mem 4 MiB por nodo de ejecución y
maintenance_work_mem 64 MiB; work_mem no es un máximo global de sesión.
Límites de contenedor: backend 2 GiB/160 tareas, PostgreSQL 1 GiB. Dos workers
permiten hasta cuatro parsers SS-06 con 512 MiB de espacio virtual cada uno;
espacio virtual no equivale a RSS. GIS, spool multipart, buffers y exportaciones
comparten el presupuesto real: estos límites requieren medir el corpus y la
concurrencia esperada antes de QA de capacidad, no acreditan un SLA.

## Verificación aislada

Los scripts opt-in de `tests/qa/` no crean ni arrancan infraestructura. Preparar
fuera del repositorio un proyecto desechable sin puertos publicados, con redes
internas, uploads nuevos y PostgreSQL en tmpfs. Nunca reutilizar un volumen de
datos ni un archivo .env institucional. Aplicar migraciones canónicas hasta 032
mediante el runner oficial de ese laboratorio, y sólo allí.

Contrato del laboratorio: DB `software_pa_test`, cluster_name
`pr6-deployment-disposable`, runtime `ss12_runner`, hostname de certificado
`ssalfer.qa.invalid`, `PR6_DEPLOY_QA=SYNTHETIC_DISPOSABLE_ONLY` y credenciales
sintéticas explícitas en variables `POSTGRES_ADMIN_*`, `DB_RUNTIME_*`, `DB_*`,
`QA_USERNAME=ss12-qa@example.invalid`, `QA_PASSWORD`. Las variables de
autenticación deben reproducir producción: Secure, origen HTTPS exacto, proxy
confiable exacto y UPLOAD_ROOT=/app/uploads. El certificado de laboratorio se
verifica con su CA en `/qa/fullchain.pem`; no usar un certificado público real.

`seed_deployment_controls.py` sólo acepta una DB marcada y sin usuarios;
crea el fixture sintético y comprueba checksums 031/032. Se ejecuta como root
**dentro del runner desechable**, con ese único volumen de uploads. Ejecutar
`verify_deployment_controls.py` como UID 10001 con acceso sólo al laboratorio;
requiere los helpers de `backend/tests/_document_samples.py` y el fixture de
seed. `verify_deployment_account_limits.py` comprueba el bloqueo PostgreSQL;
`verify_deployment_permissions.py` reproduce la transición de propietario en
tres entradas exactas, sólo dentro de ese volumen sintético. No ejecutar estos
dos scripts con datos institucionales ni mezclar sus sesiones de prueba.

`verify_deployment_browser.cjs` requiere Playwright 1.62.1 en
`/opt/pr6-browser/node_modules/playwright`; su contenedor sólo se conecta a la
red de entrada, sin acceso a la red de datos. Los tiles externos se bloquean:
se comprueba la geometría Canvas local, login y descarga Excel. El navegador
tolera el certificado de laboratorio; el verificador HTTP realiza la prueba
con validación CA. Usar un peer de prueba con cuota disponible para login;
esperar la recuperación de la cuota si se reutiliza su IP. La CSP sigue en RO.

Mantener scripts de provisión, archivos de entorno, certificados, logs y
resultados fuera del repositorio. Al concluir, retirar sólo los contenedores,
redes y volúmenes desechables identificados por el proyecto de laboratorio.
