# SS-09 etapa 1: inventario de dependencias y artefactos declarados

Fecha: 2026-10-29. Software-PA, rama dev, HEAD `683ff75613768de28a7127c7e33a6e2ef4fc40ff` más remediaciones locales. **No es SBOM del entorno instalado, ni inventario del artefacto desplegado.** [Informe](SS-09-ETAPA1-CORRECCION-2026-10-29.md), [plan](SS-09-PLAN-CADENA-SUMINISTRO.md).

## Niveles de evidencia

| Fuente/componente | Versión declarada | Resolución conocida | Hash/digest | Procedencia acreditada | Vulnerabilidades | Pendiente |
|---|---|---|---|---|---|---|
| Python requirements |42 pins exactos |No se resolvió el grafo ni se consultó METADATA instalado |Sin hashes de wheels/sdists |Comentario dice extraído de contenedor funcional; no se acredita esa instancia |SCA no realizado en esta etapa |Grafo completo, índices, archivos seleccionados, hashes, plataforma, paquetes realmente instalados |
| React package.json/lock |14 dependencias raíz, rangos npm |Lockfile v3:123 entradas de paquetes además de raíz, con versión exacta |123 SRI con formato válido, mayormente sha512; no se verificaron tarballs |Todas las referencias resolved actuales apuntan a registry.npmjs.org sin credenciales/query; no se descargó/verificó upstream |Pendiente |npm ci nativo/peer/optional/plataforma, bytes de distribuciones y árbol instalado |
| SSALFER vendors |Leaflet1.9.4, SheetJS0.20.3, ExcelJS4.4.0, html2canvas1.4.1, Bootstrap Icons1.13.1 por nombres/banners/README |20 archivos locales actuales: recursos, licencias y documentación de vendor |SHA-256 local calculado por archivo y tamaño |README afirma fuentes/verificaciones previas; no se revalidan autenticidad ni tarballs upstream aquí |Pendiente |Comparación upstream autorizada, licencia/transformaciones y cadena de revisión |
| apt backend |gdal-bin, libpq-dev, gcc |No resuelto |No hashes/versiones Debian fijados en Dockerfile |Índice apt de la base, configuración/fecha efectiva desconocidas |Pendiente |dpkg, origen/snapshot, repositorio/firmas y dependencias transitivas |
| GDAL/GEOS/PROJ/libpq |GDAL vía apt, libpq-dev; GEOS/PROJ transitivos esperables, no versionados |Instalación/enlace real no observado |Desconocido |No se inspecciona imagen o sistema institucional |Pendiente |ABI, librerías cargadas, formatos/CRS, versiones nativas reales |
| PostgreSQL/PostGIS |Etiqueta15-3.3 del servicio |No equivale a versiones exactas aplicadas |Sin digest conocido |Referencia de imagen, no imagen descargada/comprobada |Pendiente |Digest/plataforma, versión server/extensión y privilegios SS-07 en QA autorizado |
| Imágenes base y servicios |6 referencias distintas en11 sitios Dockerfile/Compose |Etiquetas/nombre, no contenido resuelto |Ningún digest real verificado |Referencias declaradas a repositorios conocidos; no se consultó registry |Pendiente |Manifiestos multiarch, digest de plataforma, imagen construida y artefacto desplegado |
| Build/CI |pip/npm/apt y gcc; herramientas heredadas de base |Versiones exactas de pip/npm/compilador/OS desconocidas |No atestación del build ni SBOM encontrado en el flujo inspeccionado |No workflows locales; controles efectivos GitHub no observados |Pendiente |Toolchain, build de QA, procedencia firmada y revisión antes de publicar |

Los campos `installed_version`, `distribution_hash`, `actual_image_digests` y versiones nativas no observadas se dejan null/desconocidos, no se rellenan a partir de etiquetas o del Python local del auditor.

## Python:42 entradas del archivo runtime

El comentario de requirements.txt afirma un bloqueo obtenido del contenedor de desarrollo. Un freeze plano puede mezclar directas, transitivas, pruebas y paquetes ya instalados; **no acredita cierre reproducible ni topología**. El AST de app muestra imports de siete distribuciones mapeadas; eso es evidencia de uso directo en código, no una afirmación de que las otras35 sean todas transitivas o innecesarias. Scripts/auxiliares y extras pueden requerirlas.

| Paquete normalizado | Pin declarado | Evidencia de relación con app | Estado de artefacto |
|---|---|---|---|
| `aiofiles` | `25.1.0` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `annotated-doc` | `0.0.4` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `annotated-types` | `0.7.0` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `anyio` | `4.14.1` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `bcrypt` | `5.0.0` | Sí, candidato a dependencia directa | Sin hash de distribución ni versión instalada acreditada |
| `certifi` | `2026.6.17` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `cffi` | `2.0.0` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `click` | `8.4.2` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `cryptography` | `49.0.0` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `ecdsa` | `0.19.2` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `et-xmlfile` | `2.0.0` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `fastapi` | `0.138.2` | Sí, candidato a dependencia directa | Sin hash de distribución ni versión instalada acreditada |
| `geoalchemy2` | `0.20.0` | Sí, candidato a dependencia directa | Sin hash de distribución ni versión instalada acreditada |
| `greenlet` | `3.5.3` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `h11` | `0.16.0` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `httpcore` | `1.0.9` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `httpx` | `0.28.1` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `idna` | `3.18` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `iniconfig` | `2.3.0` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `numpy` | `2.4.6` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `openpyxl` | `3.1.5` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `packaging` | `26.2` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `pandas` | `3.0.3` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `passlib` | `1.7.4` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `pluggy` | `1.6.0` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `psycopg2-binary` | `2.9.12` | Sí, candidato a dependencia directa | Sin hash de distribución ni versión instalada acreditada |
| `pyasn1` | `0.6.3` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `pycparser` | `3.0` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `pydantic` | `2.13.4` | Sí, candidato a dependencia directa | Sin hash de distribución ni versión instalada acreditada |
| `pydantic-core` | `2.46.4` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `pygments` | `2.20.0` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `pytest` | `9.1.1` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `python-dateutil` | `2.9.0.post0` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `python-dotenv` | `1.2.2` | Sí, candidato a dependencia directa | Sin hash de distribución ni versión instalada acreditada |
| `python-multipart` | `0.0.32` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `rsa` | `4.9.1` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `six` | `1.17.0` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `sqlalchemy` | `2.0.51` | Sí, candidato a dependencia directa | Sin hash de distribución ni versión instalada acreditada |
| `starlette` | `1.3.1` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `typing-extensions` | `4.15.0` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `typing-inspection` | `0.4.2` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |
| `uvicorn` | `0.49.0` | No observado en app; función directa/transitiva pendiente | Sin hash de distribución ni versión instalada acreditada |

También `backend/tests/requirements-convenio-report.txt` declara jsonschema4.10.3 como dependencia de pruebas. No se instala ni se trata como paquete efectivo del runtime. pytest/pluggy/iniconfig/Pygments están en el archivo principal; separar runtime/QA es propuesta, **no se eliminan ni cambian versiones ahora**.

Python3.11 aparece en el tag de base, pero su parche/OS/pip/arquitectura no están fijados por digest. No se activa --require-hashes: faltan distribuciones elegidas por plataforma y hashes verificables del grafo completo. No se comparó con lo instalado en un contenedor ni con PyPI; no hay conclusión de compatibilidad o ausencia de CVEs.

## Node.js React/Vite

package-lock.json tiene124 entradas incluyendo la raíz vacía. Las123 de paquetes pueden contener duplicados por posición, dependencias opcionales/dev y resoluciones anidadas; no son123 paquetes únicos necesariamente ni123 paquetes instalados en toda plataforma.109 posiciones adicionales a las14 directas no deben clasificarse automáticamente como presentes en runtime del navegador. La imagen final copia dist, no node_modules, pero el build usa devDependencies.

| Dependencia raíz | Tipo declarado | Rango package.json | Versión lock | Comprobación offline |
|---|---|---|---|---|
| `axios` | dependencies | `^1.18.1` | `1.18.1` | matches_reviewed_range |
| `leaflet` | dependencies | `^1.9.4` | `1.9.4` | matches_reviewed_range |
| `lucide-react` | dependencies | `^1.21.0` | `1.21.0` | matches_reviewed_range |
| `react` | dependencies | `^19.2.7` | `19.2.7` | matches_reviewed_range |
| `react-dom` | dependencies | `^19.2.7` | `19.2.7` | matches_reviewed_range |
| `react-leaflet` | dependencies | `^5.0.0` | `5.0.0` | matches_reviewed_range |
| `react-router-dom` | dependencies | `^7.18.0` | `7.18.2` | matches_reviewed_range |
| `wellknown` | dependencies | `^0.5.0` | `0.5.0` | matches_reviewed_range |
| `@playwright/test` | devDependencies | `^1.62.1` | `1.62.1` | matches_reviewed_range |
| `@types/react` | devDependencies | `^19.2.17` | `19.2.17` | matches_reviewed_range |
| `@types/react-dom` | devDependencies | `^19.2.3` | `19.2.3` | matches_reviewed_range |
| `@vitejs/plugin-react` | devDependencies | `^6.0.2` | `6.0.3` | matches_reviewed_range |
| `oxlint` | devDependencies | `^1.69.0` | `1.71.0` | matches_reviewed_range |
| `vite` | devDependencies | `^8.1.0` | `8.1.0` | matches_reviewed_range |

Las123 entradas actuales contienen SRI sintácticamente válido y resolved HTTPS a registry.npmjs.org. Se conserva ese SRI declarado en [inventario JSON](ss09/inventario-declarado.json), sin afirmar que un tarball se descargó o coincidió. El verificador nunca muestra userinfo/query de un resolved inseguro, ni URL de registry nueva no revisada.

El Dockerfile usa npm ci, que es una base útil para instalar desde lock sin reescribirlo, pero no elimina riesgos del registry, scripts o toolchain. El lock marca hasInstallScript en dos posiciones de fsevents (una anidada en playwright); su ejecución efectiva depende de selección/plataforma y no se observó. No se ejecutaron npm, Vite, Playwright o scripts package.json. [Referencia npm ci](https://docs.npmjs.com/cli/v11/commands/npm-ci/).

El verificador compara dependencias raíz JSON/lock y aplica un subconjunto explícito de semver a los rangos simples exactos/^/~ actuales. No resuelve peerDependencies, overrides, workspaces, integridad de tarballs, enlaces o todo semver npm. Una sintaxis nueva no compatible queda pendiente/rechazada para revisión, no se “resuelve” de forma inventada.

## Vendors: manifiesto SHA-256 local

[Manifiesto revisable](ss09/vendors-sha256.json). Contiene los20 archivos actuales, incluidos licencias/README para mantener trazabilidad. Integridad local significa igualdad de bytes contra esta referencia; **no prueba que el archivo original fuera auténtico ni resistente a una modificación conjunta de vendor y manifiesto**. La referencia debe revisarse/fijarse mediante Git/procedencia antes de usarla como control de publicación.

| Archivo relativo a js/vendor | Versión declarada de familia | Bytes | SHA-256 local actual |
|---|---|---|---|
| `EXCELJS-LICENSE.txt` | 4.4.0 | 1084 | `2ed526b7e7c7681dc2347995b5036ddf73dc27d0539cdea59b6d4a72b63a57a0` |
| `HTML2CANVAS-LICENSE.txt` | 1.4.1 | 1061 | `86200ce4e92d9a22c41c8647a55f7a5fddff304ff89b4d36ecc699ed8c123d2c` |
| `README.md` | No aplica | 1270 | `83bdd4ab077b4c4fc4bc821a87513088f88d7cd5b2ca669b2e8d2ba50d25a879` |
| `SheetJS-LICENSE.txt` | 0.20.3 | 11355 | `4d2a38ac35cda06a555c84074a819d413339cd3691b822cae50f8f322fe01f64` |
| `SheetJS-README.md` | 0.20.3 | 498 | `22e910300bc86e3517e6d6b6b1fe4e12dba3d4a72fe03141d18f927cc83c0d58` |
| `bootstrap-icons-1.13.1/LICENSE.txt` | 1.13.1 | 1093 | `0fb3e11bd57e896c5a512afd64864d28a37de45d19835016c87ca1ad19ead969` |
| `bootstrap-icons-1.13.1/bootstrap-icons.css` | 1.13.1 | 99556 | `004322721c8557331759bc6ddaacbb689b0f0715d688aec82bd056d2d5b5cc3b` |
| `bootstrap-icons-1.13.1/fonts/bootstrap-icons.woff` | 1.13.1 | 180288 | `f55513b7b591cb84a3b87ff0e34ea24d4831d6fedc22e54b911ca64b5b544a15` |
| `bootstrap-icons-1.13.1/fonts/bootstrap-icons.woff2` | 1.13.1 | 134044 | `6c75710364a1ca5604267716f6d28997b26319fdb078cf11e0b42ab66ff2ea61` |
| `exceljs-4.4.0.min.js` | 4.4.0 | 947702 | `7e49da68588e250dbb8bba190d2caa8ab3787cc0284bda1d8b2f805c4df742c9` |
| `html2canvas-1.4.1.min.js` | 1.4.1 | 198689 | `e87e550794322e574a1fda0c1549a3c70dae5a93d9113417a429016838eab8cb` |
| `leaflet-1.9.4/LICENSE.txt` | 1.9.4 | 1369 | `bbc959aaef7488b38942e7f05cfd1244351f8bce54261951ea17dd7cf60f894b` |
| `leaflet-1.9.4/images/layers-2x.png` | 1.9.4 | 1259 | `066daca850d8ffbef007af00b06eac0015728dee279c51f3cb6c716df7c42edf` |
| `leaflet-1.9.4/images/layers.png` | 1.9.4 | 696 | `1dbbe9d028e292f36fcba8f8b3a28d5e8932754fc2215b9ac69e4cdecf5107c6` |
| `leaflet-1.9.4/images/marker-icon-2x.png` | 1.9.4 | 2464 | `00179c4c1ee830d3a108412ae0d294f55776cfeb085c60129a39aa6fc4ae2528` |
| `leaflet-1.9.4/images/marker-icon.png` | 1.9.4 | 1466 | `574c3a5cca85f4114085b6841596d62f00d7c892c7b03f28cbfa301deb1dc437` |
| `leaflet-1.9.4/images/marker-shadow.png` | 1.9.4 | 618 | `264f5c640339f042dd729062cfc04c17f8ea0f29882b538e3848ed8f10edb4da` |
| `leaflet-1.9.4/leaflet.css` | 1.9.4 | 14145 | `337bfca5cabd03b39815b2700febe2b3b7edf55921c59cd49f88ecb328212303` |
| `leaflet-1.9.4/leaflet.js` | 1.9.4 | 147552 | `db49d009c841f5ca34a888c96511ae936fd9f5533e90d8b2c4d57596f4e5641a` |
| `xlsx-0.20.3.mini.min.js` | 0.20.3 | 279523 | `0cb353f830d7288385492c83d277b058ddeac664ca51cf1393aa1fd3e2b70939` |

ExcelJS es un caso importante: su banner tiene fecha, no aparece la cadena4.4.0 en el JS. Esa versión procede del nombre/README, no de una declaración interna acreditada. Leaflet, SheetJS, html2canvas y Bootstrap Icons sí contienen literales/banners coincidentes en su archivo principal; eso sigue sin autenticar los bytes.

Las afirmaciones SHA previas de README para ExcelJS y SheetJS coinciden con los hashes locales actuales. Se comprueba únicamente consistencia local entre textos/bytes; no se reejecuta la verificación de tarball/dist.shasum que el README afirma. Licencias presentes no demuestran autenticidad o exhaustividad de dependencias embebidas; revisar la distribución upstream completa con autorización.

Código propio HTML/JS/CSS queda separado de js/vendor; las dependencias npm de React son otro árbol. No se reemplazan librerías, no se cambia el frontend seleccionado ni se envían los archivos/hashes a scanners externos. No se añade una comprobación en navegador que altere cargas de SSALFER; es un control offline para revisión/build futuro.

## Imágenes, nativos y herramientas

| Referencia declarada | Ubicación | Estado / riesgo |
|---|---|---|
| python:3.11-slim |backend/Dockerfile |Tag mutable; SO/patch/digest/arquitectura desconocidos. pip heredado, apt y compilación permanecen en runtime |
| node:22-slim |frontend/Dockerfile |Tag mutable; versión exacta Node/npm desconocida. Etapa npm ci y etapas dev/build, no selección probada del artefacto final |
| nginx:1.27-alpine |Dockerfiles SSALFER y React production |Tag mutable; bytes/digest no comprobados. SS-08 añade headers/COPY selectiva sólo a SSALFER, preservados |
| postgis/postgis:15-3.3 |Compose base y QA |Tag mutable; ni versión exacta server/extensión ni GEOS/PROJ acreditados |
| dpage/pgadmin4 |Compose base |Sin tag explícito; no fijación por digest. No se actualiza ni retira sin decisión administrativa |
| software-pa-backend |Compose base/QA |Nombre mutable de imagen local/build; no se conoce ID/digest/procedencia de la instancia existente. No asumir descarga pública o correspondencia con HEAD |

GDAL está fuera de requirements como ejecutable de gdal-bin. GEOS/PROJ, librerías libgdal, cliente PostgreSQL/libpq y su enlace real requieren inventario apt/ldd/paquetes en la imagen QA. psycopg2-binary puede llevar librerías propias: no deducir su libpq cargada de libpq-dev o de la versión del servidor. PostGIS y btree_gist se declaran como extensiones en migraciones, no como paquetes Python.

No se fijan digests inventados ni se cambia plataforma/base. Para aprobar un pin futuro se necesitan metadatos del registry y plataforma y una reconstrucción compatible con todos los flujos GIS/documentales; no basta elegir el digest “latest” o una arquitectura del equipo auditor.

## Contextos y despliegue

Backend conserva COPY . ., pero se amplía .dockerignore con secretos/env/VCS/claves/backups y fuentes de tests fuera de imagen runtime. Mantiene app, requirements, logging.json, scripts y migraciones/init. El modelo de patrones es parcial y no sustituye al matcher Docker real. Cualquier secreto con otro nombre, generado durante RUN, capa previa o bind mount queda fuera de esta garantía.

SSALFER conserva íntegra la copia selectiva SS-08, pero no tiene .dockerignore propio: el contexto puede transmitir documentación/QA al builder aunque no se copie a la imagen. Esa exposición del contexto sigue pendiente y se marca en el verificador. React conserva .dockerignore con .env/.env.* y npm ci; no se retira. Los cuatro Compose principales y variantes QA se inspeccionan sin interpolar env, ni publicar valores de autenticación de fixtures. El detalle de producción/selección está en el plan y en [perfiles propuestos](ss09/perfiles-despliegue-propuestos.json), que **no son Compose ejecutable y no seleccionan un frontend**.

La evidencia del inventario se puede regenerar con el verificador offline; no representa una instalación o un despliegue institucional.
