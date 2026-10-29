# SS-09 etapa 1: plan de cadena de suministro y validación QA

Fecha: 2026-10-29. Estado: diseño para aprobación; **no ejecutar instalaciones, builds, publicación o cambios GitHub en esta etapa**. Referencia `dev`/`683ff75613768de28a7127c7e33a6e2ef4fc40ff` más remediaciones locales. [Informe](SS-09-ETAPA1-CORRECCION-2026-10-29.md), [inventario](SS-09-INVENTARIO-DEPENDENCIAS-2026-10-29.md).

## Separación de evidencias y puertas

| Etapa futura | Datos/controles necesarios | Estado actual y autorización |
|---|---|---|
| Fuentes revisadas |Commit aprobado o snapshot con diff local completo y origen; manifiestos/vendor SHA revisados |Árbol local sucio preservado; parche SS-09 revisable, no commit. Un SHA de referencia no identifica todos los cambios locales |
| Resolución Python/Node |Grafo y selección de paquetes para plataforma, metadatos y hashes de distribuciones |Sólo pins/lock locales. Descarga/resolución requiere autorización conectada separada |
| Base/nativos |Digest de índice multiarch y de plataforma, OS/repositorio/paquetes/ABI/toolchain |Sólo tags/apt no congelados. No se consultó registry ni se descargaron imágenes |
| Build de QA |Contexto revisado sin secretos, builder/receta controlados, entorno y salidas registradas |No construido aquí; no Docker ni npm/pip/apt ejecutados |
| SBOM/SCA/pruebas |Inventario realmente instalado/estático servido y bases de vulnerabilidades actualizadas verificables |Pendiente; no usar inventario declarado como SBOM final |
| Procedencia/publicación |Atestación revisada, firma/identidad de build, digest del artefacto y gate humano |Diseño, sin crear claves, activar workflows o publicar |
| Despliegue |Perfil institucional aprobado y referencia al mismo artefacto probado por digest |Frontend y manifiesto finales requieren decisión; no despliegue en esta autorización |

## Python: resolución e integridad propuestas

1. Clasificar dependencias de aplicación, auxiliares y QA desde código y METADATA del entorno conocido. El freeze actual no prueba qué paquetes son transitivos ni prescindibles. Diseñar archivos fuente/locks separados sólo tras pruebas; no eliminar pytest/passlib/otras bibliotecas por falta de import directo en app.
2. Fijar plataforma objetivo: arquitectura, OS/base por digest, CPython3.11 exacto y herramienta de resolución/pip. Resolver grafo completo con markers/extras/Requires-Python/Requires-Dist; registrar índices autorizados y restricciones, sin credenciales en URL, logs o lock público.
3. Seleccionar wheels/sdists concretos por plataforma y obtener metadatos de procedencia y hashes verificables. Para cada distribución faltan actualmente nombre de archivo, tamaño, SHA-256 autenticado, origen y selección de tags. Si hay sdist, también controlar build-system/build dependencies/compilador/ABI y el wheel resultante; un hash de sdist no fija todo el build.
4. Preparar wheelhouse o repositorio interno aprobado con retención y control de cambios. La resolución/descarga es una actividad conectada futura autorizada, no se obtiene reutilizando un entorno institucional o transmitiendo código al scanner.
5. Sólo después de cerrar y verificar todos los hashes habilitar un modo de instalación con hash checking. No pegar hashes calculados de nombres de versión o de archivos ajenos. Evaluar wheels-only cuando sean compatibles, sin asumir disponibilidad de ruedas para todos los nativos. [Instalaciones seguras pip](https://pip.pypa.io/en/stable/topics/secure-installs/).
6. Instalar/reconstruir únicamente en QA autorizado y registrar el resultado con inventario de METADATA, pip inspect/list/check u herramientas aprobadas, sin imprimir configuración/credenciales pip. Guardar wheels y salida de build según política; no ejecutar esos comandos en esta intervención.
7. Ejecutar regresiones y SCA de las distribuciones realmente seleccionadas/instaladas y sus transitivas, con base de advisories fechada y procedencia registrada. Cambios de versiones se evalúan de forma específica, con corpus GIS/documental/contratos; no actualizar todo por ser reciente.

Hash checking no autentica por sí solo quién aprobó el hash ni elimina malware válido dentro de la distribución. El archivo de hashes y la receta deben estar revisados y vinculados al build. Las bibliotecas nativas obtenidas por apt y las base images requieren controles separados.

## Node y vendors

Preservar package-lock y npm ci; fijar versión Node/npm, flags relevantes y plataforma del builder antes de reconstruir. Capturar árbol efectivo con versiones, dependencias opcionales/dev/peer y scripts de instalación ejecutados; el lock no acredita que cada entrada se instaló ni que todo devDependency termina en dist. El bundler necesita revisar lo realmente emitido; la imagen final React es distinta de la imagen Node builder.

Para vendors, revisar cada familia y ruta del manifiesto. En actividad futura autorizada, obtener distribución upstream indicada por el proveedor, su metadata/firmas cuando existan, verificar hash de tarball y extraer únicamente recursos esperados en un entorno aislado. Comparar bytes locales y documentar cualquier minificación/parche/transformación, licencia y transitive code embebido. No sustituir vendors automáticamente para hacer coincidir un hash.

Un manifiesto vendor alterado junto al archivo puede superar una verificación local: proteger su revisión y procedencia. No exponer SBOM/informes operativos dentro del document root para “demostrar” integridad. Conservar la copia selectiva SS-08 y verificar los hashes de assets de la imagen construida/servida, no sólo los de la carpeta fuente.

## Docker y dependencias nativas

Antes de fijar un digest: resolver la referencia correcta y comprobar plataforma, manifiesto de índice y digest específico. Identificar soporte de GDAL/GEOS/PROJ/libpq, formatos, drivers, CRS y geometrías Z/M. No inventar un digest o aplicar el de otra arquitectura. Tras prueba QA, actualizar referencias con aprobación y registrar origen del pin; conservar un plan de actualización porque inmutabilidad no elimina vulnerabilidades.

Para apt, registrar OS/codename, sources sin secretos, repositorios y firmas/snapshot, versiones de gdal-bin/libgdal/GEOS/PROJ/libpq/gcc y transitivas, más los paquetes realmente instalados. No suponer que la etiqueta slim o15-3.3 determina todos ellos. Congelar paquetes requiere disponibilidad de repositorio y compatibilidad; decidir entre snapshot interno/archivo y pin de paquetes mediante revisión.

Backend conserva gcc/libpq-dev y dependencias de build en runtime. Evaluar después una etapa builder separada y runtime mínimo que copie wheels/librerías necesarios, probando enlaces nativos. No retirar gcc/libpq-dev a ciegas: puede cambiar cómo se construyen cffi/cryptography u otros paquetes y romper distribución de GDAL/libpq.

SSALFER no tiene ignore de contexto propio: la copia selectiva protege el document root, pero no evita transmitir QA/documentación al builder. Diseñar exclusiones conservando deploy/nginx.conf, Dockerfile, recursos y licencias y ensayarlas después; no se alteran esas entradas en esta fase.

La exclusión .dockerignore de backend se comprueba localmente con casos simples. Docker real y posibles Dockerfile-specific ignore tienen precedencias/semántica propia que deben verificarse en QA. Revisar el contexto exacto y capas/artefacto resultante sin copiar secretos o datasets reales. [Contextos e ignore Docker](https://docs.docker.com/build/concepts/context/).

Tests ya no se copian a la imagen API mediante el contexto backend. Los Compose QA versionados montan fuentes backend (incluyendo tests), y el desarrollo usa bind: esa ruta sigue intacta. Si un procedimiento ajeno requiere tests dentro de una imagen sin mounts, crear un artefacto QA separado con autorización; no ampliar la imagen productiva otra vez ni omitir pruebas por ese cambio. .dockerignore no filtra bind mounts ni borra archivos de imágenes anteriores.

## Propuesta de manifiesto institucional único

[Perfiles propuestos](ss09/perfiles-despliegue-propuestos.json) es un descriptor de decisión, **no se ejecuta, no es un nuevo Compose y selected_profile=null**. Incluye dos candidatos para que el dueño funcional elija sin retirar React:

| Candidato | Lista de Compose explícita y ordenada | Servicios explícitos a construir / iniciar | Condiciones |
|---|---|---|---|
| SSALFER, si se aprueba |base, prod, ssalfer |Build backend/frontend_ssalfer; iniciar db/backend/frontend_ssalfer |Frontend React y pgAdmin no seleccionados por ese perfil, pero no eliminados del repositorio. Todo servicio administrativo adicional requiere decisión |
| React/Vite, si se confirma necesario |base, prod |Build backend/frontend; iniciar db/backend/frontend |No se declara obsoleto. Mantener QA propia de React; no atribuirle los headers SSALFER de SS-08 |

La selección explícita de servicios es necesaria tanto para build como para inicio: cargar base+prod+ssalfer declara ambos frontends; ejecutar sin seleccionar puede iniciarlos/construirlos a ambos. No cambiarlo mediante suposiciones del operador o inferencia del nombre del archivo. Un manifiesto final aprobado debería tener un único perfil activo, sus servicios/imágenes por digest, plataforma, receta y versión de configuración exactas, además de parámetros no secretos validados.

Requisitos del perfil final: APP_ENV production, cookies Secure/__Host-/Path correctas, CORS del origen HTTPS público exacto, comando Uvicorn sin reload y con --no-proxy-headers/SS-10 logging, archivos Compose explícitos sin override automático dev, ausencia de binds de código, puertos/volúmenes/red revisados, TLS/Host/redirecciones y cadena de confianza acreditados por QA. No incluir .env o credenciales en el descriptor, imagen o informe.

| Combinación actual | Riesgo/consecuencia que debe distinguirse |
|---|---|
| Compose implícito base+override |Desarrollo, reload/binds/Vite; no convertir en producción por sólo cambiar una variable |
| base+prod |React disponible, SSALFER no añadido; sin constancia del TLS externo |
| base+ssalfer |Añade SSALFER, no fuerza modo production/cookies seguras de backend ni retira frontend base |
| base+prod+ssalfer |Dos frontends declarados; requiere servicios explícitos y aprobación del perfil/administración |
| Dockerfile backend usado solo |CMD aún tiene reload; Compose base lo reemplaza por comando seguro de SS-04/10. No se cambia ese contrato previo en SS-09 |
| Composes QA |Destinos sintéticos/tareas de prueba, no manifiesto institucional; revisar identidad/red/binds y autorización antes de usarlos |

No se ejecuta docker compose config: puede interpolar credenciales. Una futura comprobación de configuración deberá tener una salida selectiva protegida y sin secretos, preparada por operación, con aprobación. El reconocimiento textual del verificador no calcula el modelo combinado, aliases completos, interpolación, perfiles o estado del daemon.

## GitHub: controles no observados y pipeline propuesto

No hay workflows/Dependabot versionados en el árbol inspeccionado. **Eso no acredita ausencia de protecciones, rulesets o políticas efectivas de organización/GitHub.** No se consultó una sesión/API administrativa ni se accedió a secretos. El dato histórico protected:false no demuestra el estado actual; reglas alternativas podrían aplicar. No afirmar falta de acceso por la cuenta sin haberlo consultado: aquí el control queda no observado.

Inspección futura autorizada: protección de dev y otras ramas de integración, rulesets y bypasses heredados, revisiones obligatorias/CODEOWNERS si procede, checks requeridos y permisos de merge, entornos con aprobación, políticas de acciones/runners, permisos reales de GITHUB_TOKEN, integraciones/secretos por alcance y evidencia de publicación/procedencia. No mostrar valores de secretos, sólo nombres/capacidades estrictamente necesarios bajo acceso autorizado.

Propuesta de pipeline, no workflow activado:

1. **Revisión de fuentes/manifiestos.** Verificador offline, integridad vendors y consistencia lock, análisis de cambios de Dockerfiles/migraciones/contextos. Base de ejecución fijada y datos sintéticos; sin token de publicación ni secretos de despliegue.
2. **Pruebas aisladas.** Suites de seguridad locales y regresiones SS-01/02/03/04/06/08/10/11/12; las integradas sólo en QA desechable autorizada. No importar conftest institucional ni ejecutar código de PR no confiable con secretos.
3. **Resolución y SCA autorizadas.** Bases de advisories con fecha/firma/origen; análisis local de requisitos/lock/vendors/OS/imagen final. Scanners y datos aprobados y fijados por versión/digest; no enviar código/datos/secretos a servicios externos. Documentar alcance, falsos positivos/excepciones y fecha; no igualar ausencia de resultados con seguridad.
4. **Build de QA trazable.** Receta y fuentes aprobadas, dependencias/base/apt fijadas tras validar plataforma; SBOM y evidencia del build. Bloquear red adicional/credentials innecesarias según diseño, sin imponer cambios no probados a GDAL.
5. **Verificación del artefacto.** Pruebas nativas y comparación de manifiesto/vendor assets dentro de la imagen; escaneo de imagen/ABI y QA HTTP/SS-08, credenciales sintéticas y privilegios SS-07 verificados por procedimiento independiente.
6. **Revisión antes de publicar.** Entorno/gate humano que aprueba resultado, SBOM/procedencia y digest. Job separado con permisos mínimos de escritura/publicación/atestación sólo cuando se autorice; no compartir token con jobs que ejecutan código no confiable.
7. **Promoción por digest.** Publicar únicamente tras aprobación y desplegar el mismo artefacto QA aprobado, sin reconstruir con tags mutables en el servidor. Despliegue requiere autorización separada, queda fuera de esta etapa.

Usar permisos de lectura por defecto y elevar por job cuando haga falta; pin completo de acciones externas por SHA verificado y actualización revisada; no inventar esos SHA ni habilitar actions ahora. Proteger caches/artefactos contra contaminación y rutas de checkout de código no confiable. [Guía de uso seguro GitHub Actions](https://docs.github.com/en/actions/reference/security/secure-use). Dependabot puede proponerse para PR revisadas, no como actualización/merge/despliegue automático autorizado.

## Evidencia de reconstrucción/SBOM requerida en QA

| Artefacto/evidencia | Datos mínimos seguros |
|---|---|
| Fuente/receta |Commit aprobado más identidad del árbol/diff si aplica; hashes de manifiestos no secretos, Dockerfiles/contexto relevante, versión de receta y perfil elegido |
| Python resuelto |Grafo Requires-Dist/markers/extras, tags de wheels/sdists, distribución/URL aprobada sin userinfo, hash verificado, build deps, METADATA instalado y toolchain |
| Node/dist |Lock e instalación efectivos, Node/npm, flags, scripts y selección de plataforma; SBOM de build y bundles dist, no sólo package.json |
| Vendors |Manifiesto local aprobado, bytes upstream comparados y transformaciones documentadas, licencias; hashes coincidentes dentro de imagen y recursos servidos |
| Base/OS/nativos |Digest índice/plataforma, OS/paquetes repositorio, GDAL/GEOS/PROJ/libpq y librerías cargadas; no usar versiones del host auditor |
| PostgreSQL/PostGIS |Digest/versión imagen y extensión real mediante QA autorizada y sin datos de negocio. No se conecta en esta fase ni se presume igualdad con tag |
| SBOM |SPDX/CycloneDX u otro formato aprobado, herramienta/version fijadas, alcance explícito (OS/Python/Node/vendors), fecha y sujeto por digest. No publicar secretos/env/expedientes |
| Procedencia |Identidad autorizada del builder, materiales, receta, plataforma y artefactos/digests, firma/atestación verificable con clave/identidad protegida. No crear o imprimir claves aquí |
| SCA |Base de advisories/version/fecha y alcance, componentes coincidentes, justificación de impacto, excepciones y pruebas. No inventar CVEs por paquete obsoleto o ausencia de hash |
| Aceptación nativa |Auth/cookies/RBAC, documentos SS-06/12, GIS formatos/CRS/Z/M y SS-03 presupuestos, proxy/cargas/caché/CSP SS-08, reportes SS-11, logging SS-10 y rollback de imagen/configuración |

Las herramientas para SBOM/SCA o inspección de binarios sólo se instalan/ejecutan en esa fase si se aprueban. La verificación de datos nativos puede incluir versiones de GDAL/paquetes/librerías dentro de la imagen de QA; no ejecutar comandos contra el host institucional ni copiar sus secretos a un inventario. La conectividad requerida para paquetes/registries/advisories debe delimitarse por destinos y datos enviados; esta etapa no la habilita.

## Criterios de aceptación

- Perfiles/frontend y servicios elegidos con aprobación funcional; no inicio accidental de override dev, React o pgAdmin fuera del perfil.
- Digests/plataforma y dependencias/hashes verificados, sin inventarlos ni activar hash mode incompleto.
- Contexto Docker real excluye secretos/datos/QA ajenos, preserva recursos necesarios y SS-08; capas finales inspeccionadas y procedimiento de pruebas no degradado.
- SBOM y SCA de artefactos realmente construidos/instalados, evidencia nativa GIS/HTTP/DB QA autorizada y riesgos documentados.
- Controles GitHub efectivos acreditados, workflow revisado con permisos mínimos y publicación separada aprobada.
- Atestación/procedencia y digest de promoción verificables; no declarar preparado para despliegue a partir de exit0 del verificador offline.

**No se implementa pipeline, pinning, actualización de dependencias, cambio de roles/SS-05/SS-07, publicación o despliegue en esta entrega.**
