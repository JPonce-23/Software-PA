# SS-08 etapa 1: endurecimiento HTTP local y diseño de verificación

Fecha: 2026-10-29. Software-PA / SSALFER. Rama `dev`, HEAD `683ff75613768de28a7127c7e33a6e2ef4fc40ff`, más remediaciones locales existentes. Estado: **corrección parcial revisable; SS-08 permanece abierto y pendiente QA**.

## Resultado y separación de controles

Se implementan cabeceras HTTP compatibles con el código inspeccionado, CSP candidata en Report-Only, access log Nginx sin datos de solicitud y selección explícita de recursos al construir la imagen SSALFER. No se cambian roles, cookies, CSRF, CORS, confianza de proxy, API, frontend JavaScript, formatos, GIS, almacenamiento o dependencias.

La configuración institucional efectiva no fue inspeccionada. No se ejecutó Nginx, Docker, navegador, TLS, PostgreSQL, migración o servicio. No se leyeron .env/credenciales institucionales, instalaron herramientas o hicieron commits/push/merge/despliegue. Sólo se ejecutaron pruebas previamente inspeccionadas con texto/dobles/archivos sintéticos propios y Node local sin red.

| Control | Estado de esta entrega |
|---|---|
| nosniff / no-referrer / SAMEORIGIN / Permissions-Policy |Implementado en Nginx SSALFER con always; modelo estático probado, respuestas reales y posible embedding externo pendientes |
| no-store en estáticos/API y evitar caché/almacenamiento proxy explícitos |Implementado; descarga SS-06/12 conserva attachment/octet-stream y private,no-store; no se declara borrado de cachés históricas, memoria o BFCache |
| CSP |Sólo Report-Only; sin colector externo. No se declara bloqueante ni compatible para enforcement:29 scripts inline requieren resolución/QA |
| Documentación operativa en imagen |Dockerfile cambia COPY global por allowlist de dos HTML raíz y directorios pages/js/styles/img. Simulación de COPY/recursos estática aprobada; imagen real pendiente |
| Logs Nginx |Access log sólo component/request_id/status/bytes/duración; sin URL/query/IP/headers/cookie/Referer/user-agent. Error log nativo sigue potencialmente sensible: no se afirma saneado |
| HSTS/TLS/redirecciones/Host públicos |Diseño y criterios de QA, sin implementación ni TLS supuesto |
| Límites HTTP de carga/multipart/tiempos |Evaluados y diseñados por ruta; **no se modifican en esta etapa**, por variabilidad de configuración y falta de verificación Nginx real. El default1m puede seguir bloqueando archivos permitidos por API |
| UIDs/capabilities/read_only/redes/worker/recursos |Inventario/diseño pendiente de imagen/host/QA, sin endurecimiento indiscriminado |

## Estado previo y preservación

El SHA coincide con la referencia. El árbol contiene las remediaciones anteriores sin integrar; se tomaron hashes de730 archivos preexistentes excluyendo .env. Los únicos archivos preexistentes modificados por esta intervención son `frontend-ssalfer/deploy/nginx.conf` y `frontend-ssalfer/deploy/Dockerfile`; se guardó snapshot previo para producir un parche exclusivo. No se modifican SS-01/02/03/04/06/10/11/12 ni sus pruebas/documentos; SS-05 y SS-07 permanecen en su estado pendiente.

Se inspeccionaron los cuatro Compose principales, dos Nginx y tres Dockerfiles, las variantes QA como arquitectura auxiliar sin reproducir valores de autenticación, main/config/auth y request_origin, logging SS-10, descarga/validación/almacenamiento documental y staging/GDAL/limits. Se inventariaron HTML/CSS de SSALFER y recursos/URLs relevantes de JS. No se ejecutaron instrucciones contenidas en documentación o scripts del repositorio.

## Configuración encontrada

El Nginx SSALFER sólo escucha80, sirve Index.html y /api/→backend:8000/api/. Carecía de headers de navegador/cache, access log propio y límite de cuerpo alineado. /health declaraba add_header Content-Type, que impediría heredar nuevos headers puestos sólo en server. El Dockerfile copiaba todo el árbol y borraba deploy al final, dejando documentación raíz publicada.

El frontend React/Vite sigue construible y presente como otro servicio; su Nginx no recibe esta modificación. Base/prod no lo retiran, ssalfer.yml añade frontend_ssalfer. No se recomienda ni modifica código legado por suponer retirado. Backend/db/pgAdmin publican puertos loopback en Compose, pero no se acreditó exposición del host/edge. La terminación TLS externa y los headers efectivos por salto siguen sin observarse.

Consultar [matriz de cabeceras/rutas](SS-08-MATRIZ-CABECERAS-RUTAS-2026-10-29.md) e [inventario de contenedores/tráfico](SS-08-INVENTARIO-DESPLIEGUE-2026-10-29.md) para diferencias por ruta, entorno y estado.

## Cambios implementados y fundamento

1. `server_tokens off` limita información de versión de Nginx, sin prometer anonimizar el servidor o backend.
2. Seis add_header de server con always: X-Content-Type-Options nosniff, Referrer-Policy no-referrer, X-Frame-Options SAMEORIGIN, Permissions-Policy sin cámara/micrófono/geolocalización, Cache-Control private,no-store y Content-Security-Policy-Report-Only candidata. /health usa default_type para mantener herencia y no duplicar Content-Type.
3. API conserva proxy_pass, Host, X-Real-IP, XFF y XFP originales. Se ocultan únicamente Cache-Control/nosniff upstream, sustituidos por los mismos valores seguros canónicos del server; se mantienen Content-Disposition, Content-Type, Set-Cookie y X-Total-Count. proxy_cache/proxy_store off e intercept_errors off hacen explícita la intención de no cachear/publicar ni convertir códigos de error.
4. `log_format ssalfer_safe escape=json` está al nivel http del archivo incluido por la imagen estándar. Sólo registra metadatos generados: component fijo, request_id propio de Nginx, status, bytes enviados y request_time. No usa un ID suministrado por cliente. La correlación del backend SS-10 sigue siendo independiente; no se presenta como ID end-to-end.
5. Dockerfile copia sólo Index.html/dashboard.html y directorios de aplicación. No copia DEPLOY.md, ENTREGA.md, TESTING.md ni deploy/QA al document root. No altera ningún byte de HTML/JS/CSS/mapa ni versiones de vendor/base. Los directorios permitidos deben mantenerse libres de futuros datos/secretos; no es un escáner de contenido ni garantía sobre capas heredadas de la imagen.

Las reglas de [add_header Nginx](https://nginx.org/en/docs/http/ngx_http_headers_module.html) permiten herencia/always en la versión1.27; no se introduce add_header_inherit disponible en versiones posteriores. La semántica de [proxy](https://nginx.org/en/docs/http/ngx_http_proxy_module.html) requiere verificar headers upstream, cache/buffering y errores con el binario real; las pruebas de esta entrega modelan sólo las directivas declaradas. No se ocultan ni sobrescriben headers CSP bloqueantes de un futuro upstream o edge; cualquier duplicación/contradicción con infraestructura externa debe revisarse en QA.

## CSP e inventario de frontend

[Inventario estructurado](ss08/inventario-recursos.json):36 páginas,29 bloques script inline,0 style blocks,2 atributos style,0 atributos de evento HTML y0 iframe/object/embed en páginas. No se detectan src de script o stylesheet remotos en HTML. JS sí asigna eventos/estilos en runtime; esos conteos no certifican DOM final, ausencia de eval, contenido dinámico o compatibilidad de vendors.

Leaflet1.9.4 y bibliotecas de exportación son locales; el mapa carga tiles OpenStreetMap por HTTPS desde el navegador. API configurada /api y descargas/preview/exportaciones con blob requieren política específica. No se escanean URLs minificadas indiscriminadamente como si toda URL de licencia/comentario fuera un recurso activo. No se inventan conexiones de producción a partir de ejemplos comentados en env.js.

Report-Only permite observar diferencias sin bloquear el frontend; script-src self reportaría los inline conocidos. Se conserva style-src unsafe-inline como candidata para estilos dinámicos y se consideran data/blob/tiles/fonts/workers/frames. No se añade unsafe-eval ni un colector remoto para silenciar resultados. No se afirma protección CSP efectiva frente a SS-01: su corrección por textContent se preserva y se reejecuta con dobles.

## Archivos y diff exclusivo

Preexistentes modificados:

- `frontend-ssalfer/deploy/nginx.conf`.
- `frontend-ssalfer/deploy/Dockerfile`.

Nuevos de esta intervención:

- `tests/security/test_http_deployment_security.py`.
- `docs/security/ss08/inventario-recursos.json`.
- `docs/security/SS-08-MATRIZ-CABECERAS-RUTAS-2026-10-29.md`.
- `docs/security/SS-08-INVENTARIO-DESPLIEGUE-2026-10-29.md`.
- Este informe y `SS-08-ETAPA1-CORRECCION-2026-10-29.patch`.

[Parche completo](SS-08-ETAPA1-CORRECCION-2026-10-29.patch): compara los dos archivos preexistentes con el snapshot de inicio y añade sólo los artefactos propios, sin incluir el parche a sí mismo. No contiene cambios previos ni se aplica en esta intervención. Se comprueba con aplicación inversa en modo check, sin modificar archivos.

## Evidencia de pruebas ejecutadas

Las pruebas nuevas usan shlex/AST/HTMLParser/json y PyYAML ya instalado. safe_load lee Compose como texto sin resolver entorno ni cargar .env. El pequeño lector de bloques no es un parser Nginx completo ni sustituye nginx -t; la simulación de headers/logs/COPY no es un servidor/imagen real.

```text
python3 -B -m unittest discover -s tests/security -p 'test_http_deployment_security.py' -v
Ran 15 tests — OK

python3 -B -m unittest discover -s tests/security -p 'test_*.py' -q
Ran 218 tests — OK (skipped=6)

node tests/frontend-ssalfer/map-tooltip-security.cjs
33 tests, 33 pass, 0 fail
```

Resultado Python:212 aprobadas y6 omitidas, incluidas las15 nuevas aprobadas. Omisiones existentes:3 pruebas nativas SQLAlchemy/psycopg2 de SS-10,2 Starlette de SS-12 y1 parser PostgreSQL de SS-07. No se instalaron esas herramientas ni se convirtió un skip en evidencia positiva. La suite puede emitir el token fijo `document_storage` en un fallo sintético esperado; no contiene datos de expediente o excepción sensible.

La invocación inicial `node --test ...` informó un único archivo aprobado en este entorno; la invocación directa posterior mostró los33 casos de etiquetas, geometrías, estilos, capas, eventos y previsualización con dobles. No se declara una prueba de navegador por ello. Ninguno de esos casos se conectó al backend o tiles.

Las15 pruebas nuevas cubren: unicidad/herencia/always de headers para200/401/403/404/413/500/502; health; proxy y spoofing sintético con helper real SS-04; no-cache/store/intercepción; contrato documental SS-06; ausencia de TLS/HSTS/CSP bloqueante no acreditados; candidato de recursos/inline; hashes de HTML y contenido previsto de imagen; puertos/volúmenes; logging SS-10 y nuevo access log; aritmética multipart candidata sin cambiar límites. Las pruebas de regresión existentes se inspeccionaron antes de ejecutar: no importan el engine ni hacen conexiones; GDAL se dobla y los hijos SS-12 sólo manipulan archivos sintéticos privados.

También se verifican `git diff --check`, enlaces de documentos, cobertura del inventario y hashes de preservación. No se ejecutó suite backend ni collect-only con conftest PostgreSQL.

## Riesgos residuales y compatibilidad

- El límite HTTP no alineado permanece. Nginx default1m puede rechazar cargas válidas de25/100MiB antes de FastAPI. No se fija101m global porque ampliaría login y otras rutas; diseño26/101MiB por upload requiere probar normalización/slash, metadata y overrides efectivos. El [módulo core Nginx](https://nginx.org/en/docs/http/ngx_http_core_module.html) define el límite del cuerpo; no equivale a tamaño de archivo o respuesta.
- TLS/HSTS, redirecciones por esquema/Host/puerto, CORS/origen y proxies externos siguen pendientes. --no-proxy-headers preserva SS-04 y también deja el riesgo conocido de Location http detrás de TLS. No activar confianza arbitraria en XFF para corregirlo.
- SAMEORIGIN puede afectar un embedding institucional externo no documentado; Permissions-Policy puede afectar una futura función de ubicación/cámara; nosniff exige tipos estáticos correctos. Todo requiere QA de compatibilidad antes de integrar.
- no-store incrementa tráfico de assets y no elimina por sí solo cachés anteriores, memoria de UI o acceso a copias ya guardadas. Validar atrás/adelante/logout y proxies/CDN.
- El access log mínimo elimina URL/IP del registro normal, reduciendo datos sensibles y detalle de diagnóstico. Error logs Nginx/edge pueden seguir incluyendo URI/query y contexto sensible, incluidos errores413/502; requieren acceso restringido/retención/colector seguro. No desactivar todos los errores ni prometer saneado por regex.
- proxy_cache/store off no evita buffering temporal de petición/respuesta o almacenamiento del navegador. Nginx/edge, multipart API y CSV temporal necesitan presupuestos/ACL/limpieza independientes; no se modifican buffering/timeouts sin pruebas reales.
- No hay aislamiento GDAL de proceso/UID/red/filesystem; SS-02/03 permanecen parciales. SS-12 conserva ventanas de publicación/BD, locks y descarga TOCTOU pendientes. SS-04 no tiene limitación global acreditada; headers no la sustituyen.
- SS-05 sigue pendiente de aprobación funcional y SS-07 de privilegios efectivos QA. Ninguna de esas políticas se modifica. React/Vite, backend directo, docs API y tráfico fuera de este Nginx conservan su superficie previa.
- No se endurecen usuarios/capacidades/read_only/redes/secret management/imágenes/recursos sin probar entrypoints/directorios/volúmenes reales. Ver inventario. No se afirma que el manifiesto represente producción.

## Plan QA preparado, no ejecutado ni autorizado aquí

Todo se realiza posteriormente en una instancia desechable, con datos sintéticos, DNS/red institucional bloqueados y aprobación expresa. No reutilizar .env, cookies o DB institucional. Para probar proxy/API usar un upstream sintético que emita códigos/headers/cookies controlados; para semántica API real, un clon PostgreSQL/PostGIS independiente autorizado.

| QA | Preparación y comprobación requerida |
|---|---|
| QA01 sintaxis y build |Con la misma imagen/base y contexto, nginx -t y configuración efectiva; construir imagen sólo con autorización. Backend sintético resoluble como backend:8000, sin servicios institucionales. Verificar que el formato log está en http y que mime.types/root/index/includes son los esperados |
| QA02 headers reales |GET/HEAD/OPTIONS de HTML/assets/health/API y respuestas200/401/403/404/413/500/502 (504 si aplica). Verificar una sola nosniff/Cache-Control, always/herencia, Content-Type correcto, status/cuerpo preservados, ausencia de HSTS HTTP y CSP bloqueante no aprobada |
| QA03 errores/logs |Upstream falla, timeout controlado y body excesivo; inspeccionar salida formateada con sentinelas sintéticas de query/cookie/Referer/PII/ID de cliente. Access log no los contiene. Registrar por separado la exposición del error log/colector y su protección, sin datos reales |
| QA04 cadena proxy |Peticiones directas y mediante uno/dos proxies administrados, XFF/Forwarded/XFP/X-Forwarded-Host falsificados, peer exacto no confiable/confiable, duplicados y hops. Resolver IP conforme SS-04; no habilitar Uvicorn proxy-headers |
| QA05 HTTPS/Host |TLS local de QA con dominio/certificado confiables autorizados; origin/Host/puerto, rutas con/sin slash y Location/redirects correctos. Edge elimina/normaliza headers no confiables. HSTS sólo se diseña/emite ahí tras aprobación, sin preload/subdominios por defecto |
| QA06 autenticación |Login/logout/expiración/revocación, roles, cookie session HttpOnly y CSRF legible, Secure/SameSite/__Host-/Path/sin Domain; Origin y CSRF válidos/rechazados, CORS/preflight y credenciales correctas. No crear sesiones reales institucionales |
| QA07 documentos/reportes |Archivos sintéticos válidos por formato SS-06, histórico, permisos positivos/negativos, attachment/octet-stream/nosniff/private,no-store, CSV SS-11 por lotes, descarga/cancelación/recurso cerrado. No declarar corregido SS-12 TOCTOU con un test de headers |
| QA08 uploads/budgets |Elegir límites por ruta tras medir metadata/overrides efectivos. Archivo justo debajo/en límite/por encima, Content-Length/chunked, boundary/nombre/Unicode, duplicados/exceso de campos y rutas legacy/DDV/núcleos/parcelas/documentos/slash. Rechazo explícito sin truncar y sin ampliar login; no test de carga contra servicios |
| QA09 navegador/CSP |36 páginas, login, dashboard, seguimiento individual/colectivo, mapas/capas/tooltips/popups/zoom/eventos, blobs/PDF/XLSX/CSV, fuentes/iconos e imágenes. Tiles servidos por stub local/host QA autorizado para evitar egress real. Inspeccionar violaciones Report-Only, no convertir a enforcement por cero fallos de texto |
| QA10 cache/frame/permisos |Atrás/adelante/recarga/logout/múltiples pestañas, iframe mismo origen/otro origen, permisos de ubicación/cámara actuales/futuros. Verificar que no-store no se presenta como revocación de bytes entregados |
| QA11 artefacto/puertos |Imagen no publica DEPLOY.md/ENTREGA.md/TESTING.md/deploy/QA; assets existentes están presentes y correctos. Confirmar manifiesto Compose exacto, no override dev/reload accidental, puertos loopback reales y servicio correcto (SSALFER vs React) |
| QA12 contenedores/recursos |UID/capacidades/directorios temporales/volúmenes/ACL/hardlinks/fsync, logs/retención y límites host medidos; diseñar worker SS-02 y presupuestos integrales separadamente. No imponer read_only o cambios de UID para “pasar checklist” |

Pruebas nativas omitidas: todas QA01–QA12. Tener un binario/browser instalado no sustituye esta aprobación; no se ejecutaron nginx -t, Docker build/config, curl a servidores, navegador o TLS en esta etapa.

## Condiciones antes de autorizar despliegue

1. Aprobar el diff exclusivo y ejecutar QA01–QA12 pertinentes con evidencia de éxitos, rechazos y omisiones; no confundir los212 tests Python/33 Node con tráfico real.
2. Acreditar origen público/edge/TLS/headers/proxy y corregir de forma revisada Host/esquema/puerto; preservar SS-04 y sesiones/CSRF.
3. Resolver el límite HTTP de cargas y presupuestos de proxy/parser/temporales con valores efectivos, sin bloqueos legítimos o ampliación arbitraria del login. Definir timeouts y cancelación real; no prometer cancelar PostgreSQL/GDAL por un timeout HTTP.
4. Verificar CSP Report-Only y aceptación de SAMEORIGIN/Permissions-Policy/no-store/MIME; cualquier enforcement o embedding distinto requiere revisión explícita.
5. Confirmar logs/error collector protegidos, manifiesto/imagen/puertos/volúmenes efectivos y recursos por host; mantener pendientes SS-02/05/07/12 como riesgos no cerrados.

**Entrega detenida para revisión técnica. No se integra, despliega ni continúa automáticamente otra etapa.**

## Trazabilidad de los archivos preexistentes

SHA-256 antes y después; permite comprobar que el parche parte del árbol local de inicio y no de un agregado de remediaciones anteriores.

| Archivo | SHA-256 de inicio | SHA-256 tras SS-08 |
|---|---|---|
| `frontend-ssalfer/deploy/nginx.conf` | `c7c6112ce5201b67546196a2cc32c096b874b0a429f77b27260a703e28aa5b2e` | `f6f91064d3552239ac17f5968738f0105ff2fea17ea74455314bf50e90a44b9b` |
| `frontend-ssalfer/deploy/Dockerfile` | `0f84d5ff327417a330c014cfba510bff4e3bdd0bf2ae470dea86372bf7e55edb` | `af0ee10c1e87274745b7f61c554933b536272da21c00345c537ba07169c4e4bc` |
