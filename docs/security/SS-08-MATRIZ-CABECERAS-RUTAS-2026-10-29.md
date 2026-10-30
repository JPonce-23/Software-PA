# SS-08 etapa 1: matriz de cabeceras y rutas

Fecha: 2026-10-29. Rama `dev`, HEAD `683ff75613768de28a7127c7e33a6e2ef4fc40ff` más remediaciones locales preservadas. **Estado: diseño/configuración comprobados estáticamente; respuestas HTTP reales pendientes QA.** Ver [informe](SS-08-ETAPA1-CORRECCION-2026-10-29.md) e [inventario de despliegue](SS-08-INVENTARIO-DESPLIEGUE-2026-10-29.md).

## Cabeceras del Nginx SSALFER

Todas las add_header nuevas están en server y llevan always. Ningún location declara add_header: /health usa default_type text/plain para conservar la herencia, en lugar de añadir Content-Type como segunda cabecera. Nginx1.27 hereda add_header del padre sólo si el hijo no tiene las suyas; no se usa add_header_inherit de versiones posteriores. [Documentación Nginx](https://nginx.org/en/docs/http/ngx_http_headers_module.html).

| Cabecera/control | Antes en SSALFER | Configuración local de esta etapa | Compatibilidad, ubicación y límite |
|---|---|---|---|
| X-Content-Type-Options | Ausente en Nginx; descarga API ya nosniff por SS-06 | nosniff, always | Valor canónico en Nginx; se oculta la copia upstream API para no duplicar. MIME de JS/CSS depende de mime.types de la imagen y necesita nginx/navegador QA |
| Referrer-Policy | No declarada | no-referrer, always | Evita enviar Referer incluso a tiles externos; Origin/CSRF no se elimina ni modifica. Analítica basada en Referer puede variar; no cambia URLs de recursos |
| X-Frame-Options | No declarada | SAMEORIGIN, always | Impide enmarcado externo en navegadores compatibles. No se detectaron iframe/object/embed de aplicación; embedding institucional externo no acreditado y requiere decisión/QA |
| Permissions-Policy | No declarada | camera=(), microphone=(), geolocation=(), always | No se detectó uso de esas APIs en código propio; no restringe clipboard, fullscreen o descargas. Leaflet no equivale a geolocalización del dispositivo |
| Cache-Control | Sin política Nginx; documentos ya private,no-store | private, no-store, always, también HTML/JS/CSS/health | API oculta sólo la cabecera upstream y emite el mismo valor canónico. Más transferencias por recarga; no borra cachés anteriores, DOM/memoria, BFCache o copias ya descargadas por sí solo |
| Content-Security-Policy-Report-Only | Ausente | Candidata, always | No bloquea recursos ni corrige XSS por sí sola. Hay29 scripts inline que generarían violaciones de script-src self; se conservan y no se activa enforcement |
| Content-Security-Policy (bloqueante) | Ausente | No implementada | No cambiar a enforcement antes de resolver inline, vendors, styles, blobs y conexiones en navegador QA |
| Strict-Transport-Security | Ausente; sólo HTTP80 | No implementada | Emitir en terminador TLS verificado del origen público, después de validar certificado/dominio/redirecciones y políticas. No imponer includeSubDomains/preload o HSTS a HTTP local |
| Server | Versión no restringida en este server | server_tokens off | Oculta versión de Nginx en cabecera/páginas generadas, no el nombre nginx ni otros indicadores del stack. Edge/backend directo pueden emitir información propia |
| Content-Type | Proveedor estático o API; health tenía add_header | Se preserva proveedor; health default_type text/plain | Documentos siguen application/octet-stream; no hay header global que convierta respuestas API a HTML o texto |
| Content-Disposition | Attachment backend en documentos | No se oculta ni reemplaza | Nombre saneado/attachment siguen dependiendo de SS-06 y autorización/ruta de backend |
| Set-Cookie | Backend | No se oculta, reescribe ni fabrica | HttpOnly, Secure, SameSite, Path y nombres __Host- siguen siendo de configuración backend. No se fuerza Secure desde un proxy HTTP local para compensar TLS desconocido |
| Access-Control-* y X-Total-Count | CORS/contratos backend | Se dejan pasar | No se añade wildcard CORS, no se cambia Origin o X-CSRF-Token |

## CSP candidata, sin bloqueo

```text
default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';
img-src 'self' data: blob: https://*.tile.openstreetmap.org;
font-src 'self' data:; connect-src 'self'; worker-src 'self' blob:;
frame-src 'self' blob:; object-src 'none'; base-uri 'self';
form-action 'self'; frame-ancestors 'self'
```

La cadena anterior se configura en una sola línea de Content-Security-Policy-Report-Only. No se declaran report-uri/report-to ni colectores externos: la observación se prepara para consola/instrumentación QA. No hay telemetría automática de expedientes. Report-Only permite estudiar la política sin imponerla; algunas directivas pueden tener soporte o tratamiento distinto en navegadores. [Referencia de Report-Only](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy-Report-Only).

| Recurso observado | Fuente | Tratamiento candidato / verificación pendiente |
|---|---|---|
| Scripts propios y vendors | /js, incluidos Leaflet1.9.4, SheetJS/ExcelJS/html2canvas locales | self; no se detectan scripts CDN en36 HTML. Eval/dynamic Function/worker de vendors no se certifican por inventario textual |
| Scripts inline |29 bloques, sin modificar | Producen violaciones candidatas de script-src self. Antes de enforcement externalizar con revisión o diseñar nonces/hashes por respuesta; no añadir unsafe-inline sólo para silenciar resultados sin evaluar |
| CSS local, atributos y estilos generados | styles, vendor CSS,2 atributos style HTML y CSSOM/Leaflet | style-src self unsafe-inline inicialmente candidata. No asegura compatibilidad con todas las inserciones dinámicas; requiere navegador |
| Fuentes | CSS/vendor local; referencias data posibles | font-src self data; no se detecta stylesheet remoto en HTML |
| Tiles | mapa.js usa https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png | img-src permite subdominios de tile.openstreetmap.org. Peticiones salen del navegador al proveedor; no pasan por backend y siguen sujetas a política institucional de egress/privacidad |
| API | env.js fija /api | connect-src self. Si un despliegue autorizado modifica API_BASE_URL/origen, revisar CSP/CORS en conjunto; el fallback localhost permanece pero no se presume seguro en producción |
| Exportaciones/preview | URL.createObjectURL en documentos/reportes | blob en img/frame/worker candidata; top-level blob/download/PDF viewer requiere QA. No se altera MIME, bytes o archivo guardado |
| Enlaces externos | Navegación a sitio institucional público, no script externo | No convertir cada href o URL de comentario/vendor en dependencia de ejecución. no-referrer limita datos enviados al navegar |

No usar frame-ancestors Report-Only como prueba de clickjacking bloqueado: el control bloqueante implementado es X-Frame-Options SAMEORIGIN. No se activa sandbox ni upgrade-insecure-requests, que podrían alterar login, descargas, HTTP local o navegación.

## Rutas y estados: emisión esperada, no tráfico capturado

| Ruta/contexto | Proveedor de respuesta | Cabeceras nuevas previstas | Estado y límites |
|---|---|---|---|
| `/`, `/Index.html`, `/dashboard.html`, `/pages/*.html` | Nginx SSALFER | Las seis add_header de server |200/304/404 y errores del server seleccionado; UI propia intacta, CSP sólo RO |
| `/js/`, `/styles/`, `/img/` | Nginx SSALFER | Mismas; Content-Type de mime.types | MIME correcto debe comprobarse con nosniff en imagen real; no-store reduce cache de assets |
| `/health` | return Nginx | Hereda las seis; Content-Type único text/plain |200; access_log off como antes. No acredita salud de API/BD |
| `/api/auth/*` | FastAPI vía proxy | Heredadas; Set-Cookie/CSRF/CORS backend intactos |401/403/200/201, según caso. No se implementa rate limiter SS-04 |
| `/api/documentos/versiones/{id}/descarga` | FileResponse autorizado | nosniff y private,no-store canónicos; attachment/octet-stream upstream preservados |200/206/403/404/409/500 según backend; sin mount/alias de uploads en Nginx |
| `/api/exportaciones/dashboard.csv` | Respuesta CSV SS-11 | private,no-store y demás headers; tipo/archivo upstream | No cambia límites de filas/bytes ni ciclo de recursos de SS-11 |
| `/api/proyectos/{id}/...importaciones` y carga documental | Nginx + FastAPI/GDAL | Heredadas incluso rechazo413 | Límite HTTP sigue sin alineación; el valor por defecto Nginx puede rechazar antes de API. No se presenta como resuelto |
| `/api/*` no encontrado o sin permiso | FastAPI, con intercept_errors off | Heredadas |401/403/404/500: cuerpo/código backend no se convierten en página de login ni200 |
| API caída/no resoluble en operación | Nginx | Headers del server con always |502/504, si la petición alcanza ese server; resolución de backend al arrancar puede impedir iniciar Nginx: necesita QA |
| Documentación raíz/`deploy/` de SSALFER | No copiada al document root por Dockerfile nuevo | Respuesta404 esperada con headers si no hay otro archivo de imagen/mount | No se construyó/inspeccionó una imagen real; verificar con solicitudes QA |
| `/docs`, `/openapi.json`, `/health` de FastAPI directo | Backend/edge externo, fuera de /api proxy SSALFER | No reciben automáticamente esta política | FastAPI conserva docs/OpenAPI por defecto; exposición real pendiente, no se bloquean APIs sin conocer consumidores |
| Frontend React/Vite del servicio `frontend` | Otra configuración Nginx/Vite | Sin cambios en esta intervención | Sigue construible y presente en Compose. No se declara retirado ni protegido por el Nginx SSALFER |

Las pruebas modelan herencia y always para200/401/403/404/413/500/502. No sustituyen `nginx -t`, una respuesta real, subrequests/error_page no inventariados o errores que ocurran antes de seleccionar este server. Un edge puede duplicar/quitar cabeceras: verificar cada salto y el resultado público.

## Cargas y tiempos: diseño pendiente, no configuración activa

| Presupuesto | Declarado actualmente | Propuesta para QA, no aplicada |
|---|---|---|
| Documento por archivo | Código20MiB por defecto; Compose MAX_UPLOAD_BYTES=25MiB | HTTP específico de carga mayor que límite efectivo de archivo + presupuesto explícito de metadatos/multipart;26MiB candidato para default25MiB |
| GIS comprimido/subido | IMPORT_MAX_FILE_SIZE_MB=100 por defecto (MiB en código) |101MiB candidato por ruta de upload GIS para100MiB +1MiB de overhead; no asignarlo al login ni a toda la API |
| Multipart | DDV/núcleos/parcelas controlan campos repetidos/desconocidos; legacy tiene mapeo/fuente | Acotar y aprobar campos/tamaños reales, filename/boundary, parser y temporales;1MiB de margen es hipótesis candidata, no capacidad institucional ni garantía para cualquier metadata |
| HTTP Nginx | client_max_body_size no declarado; default del módulo1m salvo configuración superior efectiva | Verificar nginx -T en QA y overrides; este problema conocido sigue abierto. No poner0/ilimitado ni relajar login para permitir GIS |
| Reporte CSV | SS-11 REPORT_MAX_ROWS=10000 y REPORT_EXPORT_MAX_BYTES=16MiB, lote250 por defaults | Mantener; un límite de entrada HTTP no limita respuesta CSV, memoria de mapa o almacenamiento temporal |
| Tiempos proxy | Sin valores específicos en default.conf; dependen de defaults/edge | Revisar connect/read/send/client_body_timeouts contra operaciones reales, sin elegir valores de infraestructura ficticios |
| GDAL / SQL / HTTP | GDAL timeout default300s; no deadline integral garantizado | Un timeout proxy puede terminar HTTP sin cancelar SQL/GDAL o limpiar transacciones. Probar cancelación real y fallos con SS-02/03/11/12, no equiparar ambos controles |

La prueba sintética sólo suma bytes de encabezados multipart +64KiB de metadata y verifica que un archivo de25/100MiB cabe en26/101MiB; no crea esos archivos, no envía tráfico y no valida los valores efectivos del despliegue. Si MAX_UPLOAD_BYTES/IMPORT_MAX_FILE_SIZE_MB se cambian, recalcular y aprobar los límites del proxy/edge antes de desplegar. No introducir regex de uploads sin probar normalización, slash, todos los flujos legacy/DDV/núcleos/parcelas y ausencia de rutas de escape.
