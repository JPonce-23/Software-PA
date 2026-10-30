SS-06 segunda etapa — implementación local, 30 de octubre de 2026

Estado: **LISTO PARA REVISAR**. Se implementaron y probaron las seis regresiones documentales. SS-06 no se declara cerrado: faltan QA integrado, corpus institucional autorizado y comprobación del artefacto desplegable.

Repositorio de trabajo exclusivo: `/home/alfredo/proyectos/Software-PA-security-qa-20261029/repo`. Se verificó árbol limpio y HEAD `292eaeaa32f533934e776aee4fcba8d9a0b0fd49` antes de crear `security/ss06-deep-validation`. La rama `security/ss01-ss12-qa` conserva ese mismo SHA. No se hizo commit, push, PR, merge, rebase o despliegue; los cambios quedan sin staging. El repositorio original `/home/alfredo/proyectos/Software-PA` no se utilizó ni modificó durante esta implementación.

La API pública de `validate_document(data, extension, client_mime, *, max_file_bytes, limits=None)` sigue en `backend/app/services/document_validation.py`; no hay un validador paralelo. Se conservan extensiones, MIME canónicos y aliases, descarga binaria, bytes originales, cuotas ZIP/XML y el protocolo de SS-12. El contraste MIME se realiza antes de lanzar el proceso para rechazar incompatibilidades sin gastar recursos de parsing.

| Brecha | Corrección implementada | Regresión |
|---|---|---|
| PDF con xref/referencias falsas | Perfil de envoltura previo más pypdf strict, rechazo de reparaciones advertidas, resolución de referencias indexadas, recorrido acotado de objetos/streams y árbol de páginas, Count, Parent, MediaBox y operaciones de contenido | xref falso, referencia inexistente, ciclo en Kids y Count falso rechazados; PDF comprimido, multipágina e incremental genuino aceptados |
| PNG con CRC correcto e IDAT inválido | Se conservan chunks/CRC; Pillow verify, reapertura y load decodifican píxeles | IDAT no-zlib rechazado |
| PNG con dimensiones excesivas | Cuotas de dimensión, píxeles y bytes decodificados, protección de decompression bombs | IHDR de 100000×100000 rechazado sin reservar esos píxeles |
| JPEG sin tablas necesarias | Se conserva la inspección de segmentos y se decodifica con Pillow, sin permitir truncados | JPEG sin tabla de cuantización rechazado; baseline/progresivo y extensiones jpg/jpeg aceptados |
| XLSX con XML secundario corrupto | ZIP/Expat inspecciona XML de hojas y demás partes XML, incluidas las declaradas XML con otra extensión; valida raíces de hojas | Hoja XML malformada o raíz incompatible rechazada; libro real con estilos generado por openpyxl aceptado |
| DOCX con XML secundario corrupto | Expat revisa también estilos, relaciones y otras partes XML; prohíbe DTD/entidades y aplica las cuotas compartidas | Styles.xml y relaciones malformados o con DTD rechazados; paquete DOCX mínimo genuino aceptado |

Se revisaron los fixtures existentes con los parsers reales: PDF, PNG, JPEG y OOXML mínimos son documentos válidos para este perfil y se conservaron. La antigua prueba que aceptaba un objeto corriente como xref stream ahora exige rechazo; el caso de aceptación usa una actualización incremental real generada con pypdf. No se relajó el validador para aceptar los antiguos ejemplos superficiales.

La inspección se ejecuta en un proceso Python nuevo con `-I -B`, sin shell, con cwd `/`, descriptores cerrados y entorno reducido a PATH/LANG/LC_ALL. La entrada viaja por stdin: no se extraen archivos ni se escriben temporales de entrada. Stdout/stderr van a DEVNULL; el resultado usa códigos de salida fijos, sin pickle ni mensajes del parser, nombres o contenido en logs/respuestas.

Antes de leer los bytes o importar pypdf/Pillow, el hijo establece límites duros con resource. Si no puede establecerlos o falta una dependencia, falla de forma cerrada: 503, sin fallback a parsing dentro del backend. Un archivo inválido o un presupuesto agotado produce 422; el tamaño vacío/excesivo conserva 413. La saturación de las dos plazas del intérprete produce 503.

| Presupuesto nuevo | Predeterminado / techo |
|---|---|
| CPU por hijo | 3 segundos, RLIMIT_CPU |
| Espacio virtual por hijo | 512 MiB, RLIMIT_AS; no es una medición de RSS |
| Espera del hijo | 5 segundos tras Popen; al vencer, SIGKILL al grupo y communicate para recogerlo |
| Hijos por intérprete | 2, sin cola propia de inspección |
| Archivos, core y descriptores del hijo | RLIMIT_FSIZE=0, RLIMIT_CORE=0, RLIMIT_NOFILE≤64 |
| Píxeles y dimensión de imagen | 20000000 píxeles y 16384 por eje |
| Memoria lógica de imagen decodificada | 160 MiB, cálculo conservador mínimo de 4 bytes por píxel |
| Frames | 1; PNG animado fuera del perfil de esta etapa |
| Páginas PDF | 1000 |
| Objetos / nodos PDF | 100000 / 200000 |
| Profundidad PDF | 64 |
| Operaciones de contenido PDF | 100000 acumuladas |
| Streams PDF decodificados | 100 MiB acumulados |

Los nuevos campos se configuran como `DOCUMENT_INSPECTION_<CAMPO_EN_MAYÚSCULAS>` a través de `load_limits`, por ejemplo `DOCUMENT_INSPECTION_WORKER_CPU_SECONDS`, `DOCUMENT_INSPECTION_WORKER_SECONDS` y `DOCUMENT_INSPECTION_WORKER_MEMORY_BYTES`. Pueden reducirse, no superar los techos anteriores. Las cuotas anteriores mantienen sus valores y reglas; ahora nodos/profundidad y bytes XML se comprueban también en las partes secundarias. No se añadieron variables a Compose ni infraestructura.

`store_version` sólo cambia para esperar la función síncrona mediante `run_in_threadpool`, evitando bloquear ASGI mientras espera al hijo. No se traslada la sesión SQLAlchemy al thread ni al hijo: autorización, consultas, hash, duplicados, numeración, auditoría, staging y publicación conservan su orden y código. Las pruebas verifican que la validación ocurre en otro thread y que las seis regresiones no llaman al staging, query de versiones, add, flush o commit. La autorización y los modelos de ese contrato se simulan; no acredita transacciones PostgreSQL ni RBAC real.

El tamaño efectivo configurado se conserva: `MAX_UPLOAD_BYTES` no cambia, el código sigue predeterminando 20 MiB y Compose/.env.example 25 MiB. No se alteraron Nginx, rutas, CSRF, permisos SS-05, SSALFER o `document_storage.py`. La recepción/spool multipart anterior a `store_version` y la discrepancia con el límite HTTP de Nginx siguen requiriendo QA separado.

Dependencias añadidas a `backend/requirements.txt`:

- `pypdf==6.21.4`: parser PDF mantenido, sin extras crypto. La distribución instalada declara Python >=3.9. [Metadatos oficiales de la versión](https://pypi.org/pypi/pypdf/6.21.4/json); [strict frente a recuperación tolerante](https://pypdf.readthedocs.io/en/stable/user/robustness.html).
- `Pillow==13.0.0`: verificación y decodificación de PNG/JPEG. La distribución instalada declara Python >=3.11. [Metadatos oficiales de la versión](https://pypi.org/pypi/Pillow/13.0.0/json); [verify no sustituye load](https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.verify).

Ambos pins se contrastaron con metadatos reales y se ejecutaron con las versiones indicadas. Son compatibles por declaración con Python 3.11 del Dockerfile; el entorno de pruebas usa CPython 3.12.3. La imagen Python 3.11 y sus codecs nativos no se construyeron ni probaron. No se actualizó el resto del lock. PyYAML 6.0.3 sólo se instaló en el venv temporal para las pruebas HTTP ya existentes; no se añadió como dependencia productiva.

SS-09 incluye ahora los dos imports y pins: inventario regenerado de 44 distribuciones, pruebas de vigencia y observación de imports actualizadas. Se conserva la clasificación `incomplete_requires_qa`, los hashes de distribución no verificados y la revisión SCA pendiente; esta modificación no afirma ausencia de CVE ni que el inventario sea un SBOM instalado.

Pruebas finales ejecutadas con datos sintéticos, sin cargar .env, iniciar la API ni conectar a PostgreSQL:

| Comprobación | PASS | FAIL | SKIP |
|---|---:|---:|---:|
| `unittest discover -s tests/security -v` | 266 | 0 | 4 |
| Subconjunto documental incluido en lo anterior | 75 | 0 | 0 |
| Nuevas pruebas profundas incluidas en lo anterior | 21 | 0 | 0 |
| SS-09 incluido en lo anterior | 25 | 0 | 0 |
| `node --test tests/frontend-ssalfer/*.cjs` | 119 | 0 | 0 |
| `git diff --check` y sintaxis de fuentes nuevas/modificadas | Conforme | 0 | 0 |

Las cuatro omisiones son una prueba de gramática PostgreSQL que requiere pglast, una prueba de objeto de excepción psycopg2 y dos de excepciones SQLAlchemy. No son fallos documentales ni autorización para ejecutar integraciones. Los tests de `tests/qa` y `backend/tests` con PostgreSQL/API quedan NOT RUN: no se acreditó un destino desechable autorizado. La suite de SSALFER usa dobles DOM/API y VM local; no sustituye navegador real.

Se comprobaron límites efectivos de CPU y memoria con procesos pequeños y deterministas, no con bombas contra servicios: el probe CPU gira bajo RLIMIT_CPU=1; el probe de memoria intenta reservar 256 MiB bajo RLIMIT_AS=128 MiB. El proceso estancado se termina y recoge al vencer el plazo de 1 s del test. También se comprueban entorno mínimo, salida descartada, dos plazas, liberación tras fallo y ausencia de cambios en los rlimits del padre. El test instrumental sustituye sólo el callback de parsing del hijo para verificar la función productiva que establece límites.

La primera ejecución completa señaló PyYAML ausente y un inventario pendiente de regenerar tras introducir el import Starlette; ambos se corrigieron. AnyIO/FileResponse y spawnSync git de Node quedaron bloqueados por el sandbox; se repitieron fuera de él con autorización. Los resultados de la tabla son de las ejecuciones finales. Evidencias temporales: `/tmp/ss06-implementation/security-tests-final.log` y `/tmp/ss06-implementation/ssalfer-tests-final.log`.

Para reproducir en un entorno Linux con las dependencias requeridas, desde la raíz del repo:

```sh
python -B -m unittest discover -s tests/security -v
node --test tests/frontend-ssalfer/*.cjs
git diff --check
```

Riesgos y pendientes materiales:

- El hijo comparte UID, permisos de filesystem y namespace de red. Los parsers reciben buffers y Expat prohíbe entidades; no se implementa un sandbox de privilegios, seccomp o red. Un fallo nativo del parser no queda contenido como en un contenedor o UID dedicado.
- Los límites son por hijo y por intérprete. El despliegue debe presupuestar memoria/CPU agregadas por workers y réplicas. La admisión de solicitudes HTTP, el spool y la espera en el pool compartido de AnyIO siguen fuera de esa cuota local.
- La creación del proceso no está incluida en el timeout de communicate; SIGKILL abrupto del backend y recuperación operativa requieren QA. No se añade una garantía de recuperación durable.
- pypdf puede asignar memoria al descomprimir antes de medir un stream: RLIMIT_AS/CPU y el proceso terminable son la defensa externa. La inspección no renderiza ni certifica conformidad completa, malware, firmas o ausencia de JavaScript/objetos activos. Los PDF cifrados se rechazan por no poder inspeccionarlos.
- XML bien formado y algunas raíces/relaciones comprobadas no equivalen al esquema OOXML completo. Fórmulas, conexiones, hyperlinks, binarios embebidos y contenedores anidados no se desinfectan. No se resolvieron recursos externos ni se utilizó extractall.
- Los techos de páginas/píxeles y el rechazo de archivos reparables o animados requieren calibración con documentos legítimos autorizados. No se relajan automáticamente si un documento no cumple el perfil.
- **SS-12 independiente:** TOCTOU de descarga por path, serialización por documento, reconciliación durable y recuperación tras commit ambiguo permanecen pendientes. La prueba nativa que reproduce sustitución de archivo sigue pasando como evidencia del riesgo; no se modificó para ocultarlo.

Archivos de alcance: `document_validation.py`, el wrapper de espera de `documents.py`, `requirements.txt`, comentario del fixture `_document_samples.py`, nueva suite `test_document_deep_validation.py`, ajustes de pruebas `test_document_validation.py`/`test_document_storage.py`, mapa e inventario SS-09, su prueba `test_supply_chain_offline.py` y este documento. No se cambiaron ramas remotas, configuración de despliegue ni archivos de otros dominios.
