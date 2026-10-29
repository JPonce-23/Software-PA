Fecha: 2026-10-29. Base original `683ff75613768de28a7127c7e33a6e2ef4fc40ff`; base candidata dev `e2699fe5c043996f7338bd63af3221957699bd65`; PR #5 observado `42ef451847dea8286c0f8d395b0d91675e62b69b`. SSALFER es el frontend oficial. **0 ramas y 0 commits creados; ningún push/PR/merge/despliegue.**

# Conciliación local con dev y PR #5

**A. LISTO PARA CREAR COMMITS del subconjunto conciliado**, después de revisión y autorización del procedimiento Git aislado. Esto no aprueba incorporar íntegramente el PR #5, no acredita QA ni producción y no cierra SS-01–12. Los controles pospuestos quedan explícitamente fuera de los futuros commits de esta etapa.

## Evidencia y construcción del espacio

El original sigue en dev/683ff75613768de28a7127c7e33a6e2ef4fc40ff, con 100 candidatos (23 modificados y 77 sin seguimiento), sin archivos adicionales al iniciar. Se revisaron los siete documentos de consolidación, se conservaron sus versiones históricas en la copia y se tomó snapshot SHA-256 de 752 archivos no sensibles. No se lee/copia .env ni su plantilla; no se ejecuta código del repositorio por instrucciones de documentación.

GitHub GET confirmó [dev](https://github.com/JPonce-23/Software-PA/tree/e2699fe5c043996f7338bd63af3221957699bd65) y [PR #5](https://github.com/JPonce-23/Software-PA/pull/5). PR #4 sigue abierto a feature/integracion-mq-deploy; ambos tienen el mismo origen. PR #5 está abierto, no Draft, 2 commits por delante y 0 detrás de dev, con dev como merge-base. Sus 175 paths se desglosan en 9 modificados, 9 nuevos y 157 eliminados. El indicador mergeable sólo describe el PR remoto; no prueba compatibilidad con nuestras remediaciones sin commit.

Se construyó un **directorio de fuentes aislado**, no un worktree Git: copia de archivos versionados/no ignorados, reconstrucción de la base con git show local de sólo lectura, contenidos de 12 archivos dev por API y bajas React ya aprobadas en dev; después combinación explícita de cambios locales. Se verificaron SHA de blob Git para los 30 archivos de texto dev/PR descargados. No se descargaron referencias/objetos Git, ni se hizo fetch/pull/checkout/merge/rebase. La copia no incluye la plantilla .env.example, deliberadamente no inspeccionada; el futuro diff no la toca. No debe confundirse con un build completo o una rama con historial.

Directorio de trabajo de esta ejecución: `/tmp/software-pa-conciliacion-20261029-n53rby8h/candidate`. Informes y evidencia externa están en `/tmp/software-pa-conciliacion-20261029-n53rby8h/reports` y `/tmp/software-pa-conciliacion-20261029-n53rby8h/evidence`. /tmp es temporal: conservar este paquete mediante el procedimiento aprobado antes de limpieza del host. No se ha creado otro QA ni accedido al QA existente.

## Incompatibilidades resueltas en la copia

- Dev/Compose: React retirado como en dev; base+prod+ssalfer describen sólo SSALFER. Servicio backend y mapa de variables compartidas son idénticos a los locales, incluidos --no-proxy-headers, --no-access-log, /app/logging.json, REPORT_*, DOCUMENT_* e IMPORT_*. Override de desarrollo conserva reload y flags, sin servicio React.
- SS-09: SOURCES separa legacy del conjunto obligatorio. Sin frontend/ se informa absent_retired, arrays Node vacíos y versiones efectivas no observadas; no se inventa una resolución histórica como instalada. Si aparece frontend/, exige sus cuatro fuentes completas y valida lock/rangos/integridad como antes. Un árbol parcial, symlink, vendor alterado/faltante o SSALFER ausente se rechaza.
- Perfil e inventario: SSALFER oficial, sin candidato React ni aprobación funcional de frontend pendiente. Perfil operativo/TLS/servicios aún requiere QA/aprobación. Se mantienen 42 pins Python +1 pin QA y los 20 hashes vendors, sin descargas/actualizaciones.
- PR #5 seleccionado: validación de origen HTTPS de producción, documentación interactiva condicional, .dockerignore SSALFER, exclusiones de secretos sin ocultar scripts QA, tres denegaciones de publicación Nginx y redacción de una dirección interna en una evidencia de rendimiento. Las pruebas del PR se reexpresan de forma aislada; no se afirma haber reproducido su laboratorio.

## Qué no se incorpora

No stack TLS/ACME/renovación, red/subred estática, UID 10001/chown, dos workers, limitador IP de 5r/m, CSP bloqueante, 101m global ni cambios de requirements del PR. No se aceptan las 157 bajas de evidencia ni reglas gitignore que ocultarían todos los .cjs/.json de deploy. Estas decisiones evitan introducir supuestos de host, borrar cobertura o perder SS-10 por reemplazo de command; requieren revisión independiente.

Los cuatro hashes CSP del PR cubren los 29 scripts inline no vacíos (4 contenidos únicos), sin atributos on* detectados en HTML. **Eso no demuestra compatibilidad de ejecución**, scripts dinámicos, bibliotecas/blob/reportes/mapas o políticas de framing. CSP sigue Report-Only. No se activa HSTS en el Nginx HTTP interno. Ver la comparación de controles para pruebas nativas necesarias.

## Resultados y límites

249 tests Python descubiertos: **243 PASS, 6 skip, 0 fallos**; SS-09 pasa 25 casos (6 nuevos) y hay 6 casos nuevos de conciliación. Node: **58 casos TAP PASS y contrato de reportes PASS**. Sintaxis de 152 Python, 36 JSON, 3 JS/CJS y 3 shell conforme. Verificador offline: integridad local conforme y 20 vendors sin cambios; no SCA/SBOM/autenticidad upstream.

El primer intento map-performance falló por sandbox spawnSync git EPERM; repetición autorizada fuera del sandbox pasó 11/11, usando sólo git show histórico local mediante GIT_DIR de lectura. Sin red ni escritura al original. Se preservan ambos logs.

El diff completo por fuentes nuevas detectó **192 avisos whitespace en 15 evidencias históricas (.patch/.md)**, todas idénticas al snapshot original. No se limpian para alterar evidencia. Ningún aviso nuevo en código/configuración conciliados. La comprobación git diff --check del original tracked es conforme; no se presenta eso como limpieza de todos los untracked. Detalles en resultados y plan de commits.

No se ejecutaron PostgreSQL/PostGIS, backend pytest/collect-only, engine/main, GDAL nativo, Docker, Nginx, TLS ni navegador. Seis skips:2 Starlette, 3 SQLAlchemy/psycopg2, 1 pglast. Los 37 scripts QA eliminados por el PR se inspeccionaron estáticamente y pueden usar navegador/HTTP/estado; no se ejecutaron. Las capturas/datasets históricos no se validaron como sintéticos ni aptos para publicación.

## Alcance de cierre y QA

SS-05 sigue diseño no aprobado; SS-07 no acredita ni modifica privilegios. SS-02 sin worker fuerte, SS-04 sin limitación distribuida/anti-bloqueo, SS-11 sin presupuesto integral del mapa/SQL y SS-12 sin serialización PostgreSQL/bitácora durable/solución TOCTOU. SS-06 no es antimalware. Todos los hallazgos siguen abiertos o parciales.

QA existente debe validar esquema/privilegios, GDAL/CRS/Z-M, cargas/descargas/SHA, concurrencia/commit incierto, filtros/totales/CSV, Leaflet/navegador, HTTPS/cookies/IP/redirects/logs y artefactos instalados. Nginx interno conserva el límite por defecto: cargas mayores de aproximadamente 1 MiB pueden fallar 413; no se declara resuelto por haber pospuesto 101m. Resolver ese presupuesto por ruta antes de aceptación operativa de uploads; no relajar login o timeouts indiscriminadamente.

La política de único origen HTTPS y OpenAPI deshabilitado en producción son cambios deliberados del PR seleccionado, cubiertos en aislamiento; QA debe confirmar que CORS real tiene un origen válido y que sus herramientas no dependen de /openapi.json público. El parser de origen no valida certificados/DNS ni toda forma de autoridad URI. El transporte/asgi scheme y Location requieren validación real con --no-proxy-headers conservado.

Ver [matriz por archivo](MATRIZ-CONCILIACION-ARCHIVOS-2026-10-29.md), [comparación](COMPARACION-CONTROLES-PR5-2026-10-29.md), [QA](GUIA-ENTREGA-COMPANERO-QA.md) y [plan Git](PLAN-INTEGRACION-SEGURIDAD-GIT.md). El candidato puede coexistir **selectivamente** con el trabajo de PR #5; aplicar todo el PR encima o fusionarlo sin conciliación no está aprobado. Si dev o PR cambian, comparar de nuevo contenido/hunks antes de crear commits.

## Verificación final del paquete

El parche acumulado nuevo CANDIDATO-CONCILIADO.patch pasó git apply --check --whitespace=nowarn sobre la proyección base-dev sin aplicar cambios. La copia contiene717 archivos,115 diferencias respecto de dev (26 modificados,89 nuevos,0 eliminados);0 borrados del PR5 aceptados. Los752 archivos originales y sus100 candidatos permanecen idénticos,índice vacío ydev activo sin nuevos commits. La reconsulta final confirmó los mismos SHA de dev yPR4/5,ambos PR abiertos ysin modificar. Ver evidence/final-preservation.json y reports/RESULTADOS-PRUEBAS-CONCILIACION.md para evidencia externa;los manifiestos yparche no se consideran commits ni una atestación de build.
