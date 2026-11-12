# SS-09 etapa 1: integridad local y trazabilidad de la cadena de suministro

Fecha: 2026-10-29. Software-PA / SSALFER, rama dev, HEAD `683ff75613768de28a7127c7e33a6e2ef4fc40ff` más remediaciones locales anteriores. **Entrega parcial validada offline; SS-09 permanece abierto.**

## Resultado

Se amplía backend/.dockerignore para excluir secretos/env/VCS/claves/backups y fuentes QA fuera de la imagen API. Se añaden un manifiesto SHA-256 de20 vendors locales, inventario reproducible de dependencias declaradas y un verificador estándar Python de sólo lectura. Se propone un descriptor institucional con selección pendiente, sin aplicar Compose ni retirar React/Vite.

No se cambian versiones, Dockerfiles, Compose, frontend, bibliotecas, código productivo API, sesiones, documentos, GIS, permisos o migraciones. SS-08 queda íntegro; SS-05 sigue en diseño y SS-07 sin verificación efectiva QA. **No se instala o descarga ningún paquete/imagen, construye artefacto o realiza conexión a servicios/DB.** Sólo se consultó documentación pública primaria sobre procesos; no se enviaron código, archivos, hashes de secretos o datos a scanners.

| Control | Estado |
|---|---|
| Exclusiones de backend build context |Implementadas como patrones; pruebas del subconjunto revisado y recursos preservados aprobadas. Matcher/capas Docker reales pendientes QA |
| Vendors SHA-256 |20 archivos actuales verificados localmente; prueba de alteración sintética rechazada. Autenticidad upstream pendiente |
| Requirements Python |42 pins inventariados; grafo, hashes de distribución, origen efectivo y versiones instaladas desconocidos |
| Node lock |14 directas y123 entradas lock de paquetes; SRI sintáctico/declared ranges simples coherentes. No tarballs ni instalación verificados |
| Imágenes/nativos |6 referencias distintas en11 sitios, sin digests reales comprobados; GDAL/GEOS/PROJ/libpq/OS instalados pendientes |
| Perfil institucional/pipeline |Diseños no aplicados; selected_profile=null, sin workflow nuevo o configuración administrativa |
| Vulnerabilidades |SCA/CVE/GHSA/OSV no ejecutados. No se afirma ausencia de vulnerabilidades ni se inventan CVEs |

## Inspección y preservación

Se inspeccionaron requirements/Dockerfiles/.dockerignore, package.json/lock, vendors/licencias/README, cuatro Compose principales y dos variantes QA, configuración/documentación de despliegue, init/runner/migraciones como consumidores de contexto, auditoría SS-09 y corrección SS-08. No se leyeron .env ni secretos administrativos o de infraestructura. Las referencias de entorno en archivos versionados se analizan sin expandirlas y no se reproducen valores de autenticación de fixtures.

Se tomó snapshot de736 archivos preexistentes excluyendo .env. El único archivo preexistente modificado es backend/.dockerignore. Las remediaciones anteriores, incluidos Dockerfiles/cabeceras/COPY de SS-08 y tests/documentos SS-05/07, se conservan byte a byte. No hubo checkout/fetch/pull/reset/commit/push/merge. El SHA de referencia no es una identificación de una imagen instalada: el árbol local incluye cambios sin integrar.

## Modificación de contexto y compatibilidad

Se conservan las exclusiones previas de venv/cache/uploads/fuentes_locales/seed_data/archivos auxiliares conocidos. Se añaden patrones raíz y anidados para .env y variantes, .git, .ssh, .aws, .pgpass, .npmrc, .pypirc, .netrc, .git-credentials; formatos comunes pem/key/p12/pfx/jks y backups/dumps. Se excluyen tests, db/tests y pytest.ini de la imagen API. No se excluyen app, logging.json, requirements, scripts, db/init o db/migrations, ni se retiran sus archivos del repositorio.

No se observan imports de tests/db/scripts como módulos requeridos por app. Las variantes QA versionadas montan las fuentes backend, por lo que los tests permanecen accesibles en ese flujo; la imagen productiva ya no es por sí sola una distribución de pruebas. Procedimientos externos que dependan de tests horneados deberán usar un artefacto QA separado o fuentes montadas y validarlo antes de integrar. No se cambian comandos/dependencias pytest ni se dejan de ejecutar las pruebas locales.

El matcher offline cubre los patrones simples revisados y comprueba casos sintéticos de exclusión y recursos; **no sustituye al matcher Docker** ni prueba que una imagen previa no contenga secretos. No bloquea secretos con nombres no cubiertos, datos insertados por RUN o bind mounts. Tampoco protege otros contextos si el operador cambia el contexto a la raíz o agrega un Dockerfile-specific ignore. Verificar contexto/capas reales en QA según [documentación Docker](https://docs.docker.com/build/concepts/context/).

## Verificador offline

Archivo: [verificar_cadena.py](ss09/verificar_cadena.py). Sólo biblioteca estándar; Linux/POSIX para O_NOFOLLOW/dir_fd. No importa app/database, dotenv, paquetes/scanners, sockets o drivers; no instala, ejecuta subprocess/shell, abre conexiones, llama Docker/npm/pip/apt/GitHub o escribe archivos. La salida JSON se emite en stdout; cualquier archivo de salida lo crea explícitamente quien lo invoca.

Uso de sólo lectura desde la raíz:

```text
python3 -B docs/security/ss09/verificar_cadena.py
```

El argumento opcional --root selecciona otro árbol de fuentes para pruebas/revisión, no una conexión. Nunca se registra la ruta completa/argumentos erróneos. Lee una lista fija de manifiestos, AST de app y vendors enumerados; no inspecciona .env, credenciales, archivos instalados o secretos de CI. Lectura por descriptores, sin seguir symlinks en las fuentes relativas y sin bloquear al abrir FIFO, sólo archivos regulares y máximo8MiB por archivo, también al observar crecimiento. Paths absolutos, escapes, material sensible y paths vendor de tipo no permitido se rechazan antes de leer. No ejecuta código de archivos inspeccionados.

La salida es determinista para el mismo árbol, sin timestamp, variables de entorno, hostname, datos personales o URL con userinfo/query. Versiones/rangos/SRI se validan con un subconjunto explícito; referencias nuevas no revisadas se omiten o marcan sin imprimir su contenido. Excepciones/errores de parser/CLI producen un código genérico, sin traceback ni valores crudos. No se promete detectar secretos camuflados como metadatos legítimos: no es secret scanner.

- Código0: inspección completada y controles de integridad/coherencia local satisfechos. **No significa seguro, SCA aprobado o despliegue listo**; assessment sigue incomplete_requires_qa con advertencias.
- Código2: alteración vendor, desajuste/coherencia no soportada, contexto incompleto, drift de contrato SS-04/08/10/prod, o error de entrada/lectura que requiere revisión. No se corrige ni regenera un hash automáticamente.

El verificador reconoce el subconjunto literal Compose del repositorio sin interpolar, aplicar merges completos o llamar compose config. Detecta etiquetas/nombres sin digest, gcc/apt declarados, COPY global y patrones requeridos, las combinaciones de entorno y ausencia de configuración local de workflows. No resuelve el ambiente combinado o una receta Docker arbitraria; no sustituye npm/pip/Docker en QA ni inspección administrativa GitHub.

El manifiesto vendor es una referencia de bytes ya presentes; si se altera junto al vendor o verificador puede requerir otra raíz de confianza. Se necesita revisión Git/atestación para autenticar la referencia. No se añade lógica a SSALFER para descargar o sustituir bibliotecas al abrir la app.

## Hallazgos comprobados y límites

1. Pins Python sin hashes y sin grafo acreditado. El comentario de freeze no demuestra distribución/entorno reproducible; no se activa --require-hashes incompleto.
2. Lock Node con123 SRI y URLs declaradas de registry, sin verificación de tarballs o árbol efectivo. npm ci sigue en Dockerfile, sin ejecución ni actualización; flags/scripts/plataforma se prueban después.
3. Vendors locales con versiones heterogéneamente declaradas: ExcelJS sólo nombre/README, las otras familias con literal/banner en principal. README documenta verificaciones anteriores, no una prueba nueva de autenticidad. Los SHA de README de ExcelJS/SheetJS coinciden con bytes locales.
4. Tags de base/servicios mutables y pgAdmin sin tag explícito; software-pa-backend es nombre mutable de build/imagen local. No se conoce digest o arquitectura; no se inventa ni modifica.
5. apt no congelado y toolchain gcc/libpq-dev dentro de runtime. GDAL/GEOS/PROJ/libpq de imagen no observados; ninguna versión del host auditor se presenta como evidencia de lo instalado en producción.
6. SSALFER carece de ignore de contexto: COPY selectiva no evita transmitir todo el contexto al builder. Backend COPY global puede incorporar archivos no excluidos; se reduce superficie mediante ignore, sin afirmar ausencia total de secretos o limpiado de capas existentes.
7. Variantes Compose pueden añadir desarrollo o ambos frontends. CMD Dockerfile backend aún tiene reload y Compose base lo reemplaza; se informa, no se altera una corrección previa. La selección institucional requiere decisión.
8. Workflows/Dependabot no presentes en el árbol inspeccionado; protecciones/rulesets/organización/secretos/atestaciones efectivas GitHub **no observados**, no se declaran ausentes. No se usa el dato histórico protected:false como estado vigente.

Son riesgos de cadena/configuración y evidencia incompleta, no CVEs nuevas confirmadas. Consultar [inventario detallado](SS-09-INVENTARIO-DEPENDENCIAS-2026-10-29.md) y [plan](SS-09-PLAN-CADENA-SUMINISTRO.md) para los datos faltantes y las puertas QA.

## Archivos de esta intervención

Preexistente modificado:

- backend/.dockerignore, sin modificar Dockerfile/dependencias.

Nuevos:

- docs/security/ss09/verificar_cadena.py.
- docs/security/ss09/vendors-sha256.json.
- docs/security/ss09/inventario-declarado.json.
- docs/security/ss09/perfiles-despliegue-propuestos.json.
- tests/security/test_supply_chain_offline.py.
- Este informe, SS-09-INVENTARIO-DEPENDENCIAS-2026-10-29.md y SS-09-PLAN-CADENA-SUMINISTRO.md.
- [SS-09-ETAPA1-CORRECCION-2026-10-29.patch](SS-09-ETAPA1-CORRECCION-2026-10-29.patch).

El parche es exclusivo: compara backend/.dockerignore con su snapshot inicial y añade sólo estos nuevos archivos; no contiene cambios SS-08 u otras remediaciones y excluye el parche a sí mismo. Se valida con aplicación inversa en modo check, sin aplicarlo ni escribir Git.

## Pruebas y evidencia

```text
python3 -B -m unittest discover -s tests/security -p 'test_supply_chain_offline.py' -q
Ran 19 tests — OK

python3 -B -m unittest discover -s tests/security -p 'test_*.py' -q
Ran 237 tests — OK (skipped=6)
```

Resultado:231 pruebas Python aprobadas y6 omitidas; las19 nuevas aprobaron. Omisiones previas:3 nativas SQLAlchemy/psycopg2 SS-10,2 Starlette SS-12 y1 parser PostgreSQL SS-07. El token fijo document_storage puede aparecer en una rama de fallo sintético esperado; no contiene datos sensibles. No se reejecuta Node/navegador porque no cambia código frontend o vendor: sus bytes y la copia SS-08 se verifican íntegros por hash y regresión estática.

Cobertura nueva: inventario determinista e igual al guardado;42/123/20 entradas; instalados desconocidos; hashes locales correctos y ExcelJS sin literal de versión; vendor alterado/nuevo no revisado/escape/symlink rechazados; lecturas sensibles/excesivas denegadas; sentinelas de credenciales en URL/metadata/argumentos no impresas; pins y lock raíz/rangos/SRI; imágenes tag vs digest sin inventar verificación; exclusiones/código/migraciones preservados; combinaciones Compose y SS-04/08/10; ausencia de conexiones/procesos/escrituras/env del verificador; políticas GitHub no observadas.

Las pruebas usan dobles/archivos sintéticos en directorios temporales propios; no leen .env real ni ejecutan scanner, Docker, pip/npm/apt, subprocess o conexiones desde el verificador. Se inspeccionaron las suites previas antes de reejecutarlas: no conftest backend/DB; hijos SS-12 sólo escriben archivos sintéticos propios. No se ejecutó pytest integrado o collect-only.

También se ejecuta el verificador real en lectura, que produce el [inventario guardado](ss09/inventario-declarado.json) con local_integrity_ok=true **e incomplete_requires_qa**. El código0 no elimina advertencias: CVE/SCA/grafo/distribuciones/nativos/GitHub/perfil siguen pendientes. Se verifican git diff --check, enlaces, preservación de736 archivos previos salvo el único ignore autorizado y parche exclusivo.

## Pruebas omitidas y requisitos de QA

- Resolución/descarga/instalación de paquetes, apt snapshots, tarballs upstream y contraste de dist/metadata/firmas: necesitan conectividad y autorización específicas. No se realizó ni se inventaron hashes.
- Docker context/build/inspect, hashes de capas/digests/plataforma y SBOM/SCA real: no ejecutados; herramientas aprobadas deben operar sobre el artefacto QA, no sólo este inventario declarado.
- Versiones/enlaces nativos de GDAL/GEOS/PROJ/libpq y PostgreSQL/PostGIS: requieren imagen QA y, para server/extensión, conexión QA aparte autorizada; no tocar infraestructura institucional.
- GitHub policies/workflows/secrets administrativos/procedencia: no consultados o modificados. Ausencia local no demuestra ausencia efectiva. Nueva revisión debe registrar alcance/fecha sin valores secretos.
- Pruebas de compatibilidad de imagen, GIS formatos/CRS/Z/M, documentos/bytes/SHA/locks, HTTP/cookies/CSP/descarga, roles y reportes: pendientes de reconstrucción nativa autorizada. Los tests aislados no las sustituyen.

## Riesgos residuales y aceptación

No se acredita autenticidad upstream, ausencia de malware/CVEs, reproducibilidad bit a bit o correspondencia con producción. Los controles GitHub, datos instalados, secretos con otros nombres/binds/capas, defaults de imagen, scripts de instalación, apt/toolchain y selección de perfil siguen siendo riesgos. El manifiesto vendor necesita revisión/procedencia protegida; no basta regenerarlo tras un fallo.

Antes de autorizar despliegue: aprobar perfil institucional/servicios, resolver y verificar distribuciones/digests/plataforma, reconstruir contexto real sin secretos, obtener SBOM/SCA/atestación del artefacto final, pasar QA de remediaciones y acreditar controles GitHub. Mantener pendientes SS-02/03/04/05/07/08/12 según sus propios informes; SS-09 no los cierra.

**Detenerse para revisión técnica. No publicar, integrar, activar workflows o desplegar a partir de esta entrega.**

## Trazabilidad del cambio de contexto

| Archivo | SHA-256 al inicio de SS-09 | SHA-256 tras SS-09 |
|---|---|---|
| `backend/.dockerignore` | `223071357c9f018eef7d3582af9d89d3ba9ac3fe5b72a96e6c3f81c81bc58de3` | `eec6ba694e1b109285adf9802d8aa3e1a5c33dac9e1df90bd0643e5279f9978b` |
