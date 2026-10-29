# SS-06 etapa 1 — Reconocimiento documental acotado y MIME del servidor

Fecha: 2026-10-28. Software-PA / SSALFER. Rama dev, HEAD `683ff75613768de28a7127c7e33a6e2ef4fc40ff`, más correcciones locales SS-01, SS-02, SS-03, SS-04, SS-10 y SS-11.

## Dictamen y alcance efectivo

**Corrección local parcial implementada y comprobada de forma aislada; QA integrada pendiente.** Se conservan PDF, DOCX, XLSX, JPG/JPEG y PNG. La carga ya no acepta únicamente una extensión: incorpora reconocimiento de envoltura/estructura básica y presupuestos de inspección. El MIME persistido de las nuevas versiones lo determina una tabla del servidor, nunca el valor del cliente.

**No es un validador completo de PDF, imágenes u OOXML, ni un antivirus, CDR o verificador de firma digital.** Un archivo que supera este perfil todavía puede estar corrupto en partes no interpretadas, contener contenido activo/malware o ser políglota. Se incluye una prueba que demuestra expresamente esa limitación. No se declara resuelto el análisis seguro de contenido ni se certifica preparación institucional por inspeccionar cabeceras/CRC.

Las descargas de **todas las versiones**, nuevas e históricas, usan application/octet-stream, attachment, nosniff y private,no-store. Se elige esa compatibilidad conservadora porque el esquema actual no distingue una versión validada de una histórica con el mismo MIME; no se supone que un MIME canónico en una fila histórica sea prueba de inspección. Las nuevas cargas sí guardan el MIME específico canónico, pero no se reutiliza ciegamente para servirlas. No hay revisión/migración automática de documentos anteriores ni parsing nuevo durante las descargas.

Resultado Python: **156 pruebas descubiertas, 153 aprobadas y 3 omitidas**. Son 28 pruebas SS-06 nuevas aprobadas y las regresiones anteriores; las tres omisiones son comprobaciones nativas previas de SS-10. No se ejecutó PostgreSQL/PostGIS, Docker, migraciones, scripts operativos, commits/push/merge o despliegues. No se leyeron .env, documentos reales ni logs institucionales; no se instalaron dependencias ni se enviaron archivos a analizadores externos.

## Inspección y preservación

Se revisaron services/documents.py, routers/documents.py, access.py, modelos/esquemas Documento/DocumentoVersion, pruebas de documentos y read models, configuración de uploads/Compose, Nginx SSALFER y consumidores DocumentosAPI. Se contrastaron SS-06 de auditoría y plan. El esquema mantiene hash SHA-256, tamaño, nombre original, ruta, MIME, versión, fecha y actor; **no tiene marca de validación de contenido, motor o perfil**.

Antes de modificar se guardaron hashes de los archivos previos y snapshots del alcance, sin leer .env. Los tres tests de integración originales no tenían cambios locales; se verificó su contenido inicial por hash antes de tomar el snapshot. Se preservan todos los códigos, pruebas e informes de remediaciones anteriores. Sólo cambian seis archivos preexistentes de este alcance, enumerados al final.

Comparación AST: la única función existente modificada en servicio es store_version, y en router download_version. Autorización, saneamiento de nombres, safe_version_path, creación/baja/vínculos y demás endpoints quedan intactos. Se verificaron idénticas las llamadas de deduplicación/hash lookup, numeración max+1, escritura, commit, rollback y compensación unlink. **No se corrige SS-05 ni SS-12**, ni se añade bloqueo/versionado concurrente, metadato histórico o migración.

## Herramientas disponibles y decisión técnica

El Python local no dispone de Pillow, pypdf/PyPDF2, defusedxml, openpyxl, FastAPI ni SQLAlchemy. Tampoco están qpdf/pdfinfo/pngcheck/jpeginfo. El requirements del backend incluye openpyxl pero no un decoder de imagen o parser PDF dedicado; no se cambia la lista de dependencias para resolverlo. /usr/bin/file ya está disponible y se utilizó sólo como comprobación local de identificación de fixtures pequeños, con stdin y entorno mínimo, no como dependencia del validador desplegado.

Se implementan comprobaciones limitadas de envoltura, no un parser completo artesanal. PDF no recorre objetos ni descomprime streams; PNG no decodifica IDAT/píxeles; JPEG inspecciona segmentos de cabecera hasta el primer SOS y no decodifica entropía; OOXML usa zipfile/Expat estándar para el contenedor y metadatos mínimos, sin extracción ni árbol XML completo. La semántica interna completa queda fuera del perfil y debe verificarse con herramientas mantenidas dentro de un worker aislado.

Expat local identificado: expat_2.6.1, con API de reparse deferral. El código la habilita cuando existe y entrega cada parte XML seleccionada en una sola llamada Parse acotada, evitando repetir tokens incompletos en feeds pequeños de versiones antiguas. Esto no equivale a demostrar ausencia de CVE ni a conocer la versión de la imagen de producción: verificar Python/Expat/zlib/zipfile y parches del artefacto real en QA.

## Perfil aceptado y rechazos

| Formato / extensiones | Comprobaciones realizadas | Qué NO demuestra |
|---|---|---|
| PDF .pdf | Cabecera en byte0, PDF1.0..1.7 o2.0, terminación %%EOF, startxref final en ventana4096 y offset dentro del archivo apuntando a xref o comienzo de objeto | No resuelve referencias, comprueba XRef stream, abre páginas, descifra, interpreta JavaScript ni verifica certificados/firmas |
| PNG .png | Firma, encuadre de todos los chunks, longitudes, CRC, IHDR único inicial con parámetros básicos legales, dimensiones no nulas, paleta cuando es indexado, IDAT presente e IEND final | No descomprime IDAT/ancillary ni acredita decodificación de píxeles, metadatos complejos o ausencia de malware |
| JPEG .jpg/.jpeg | SOI/EOI, longitudes de segmentos de cabecera, SOF con dimensiones/componentes básicos, SOS y presencia de bytes posteriores antes de EOI | No interpreta tablas Huffman/cuanti­zación, scans/entropía, Exif, thumbnails ni dimensiones de memoria del decoder |
| DOCX .docx | ZIP con directorio clásico acotado, [Content_Types].xml, _rels/.rels y word/document.xml; raíz/namespace, tipo principal DOCX, relación officeDocument interna y body directo | No valida todo el esquema OOXML, objetos incrustados, vínculos externos auxiliares, firmas de paquete ni contenido activo |
| XLSX .xlsx | Lo anterior con xl/workbook.xml, xl/_rels/workbook.xml.rels; workbook/sheets, IDs y relación a hoja/chart existente con tipo declarado compatible | No interpreta fórmulas, conexiones de datos, hojas/estilos completos, enlaces o binarios embebidos |

Se admiten namespaces principales Transitional y Strict en las partes revisadas y compresión ZIP STORED/DEFLATED. Se rechazan ZIP genéricos renombrados, DOCX/XLSX cruzados, faltas de partes obligatorias, XML roto en las partes inspeccionadas, DTD/entidades, relación principal externa, tipo principal macro-enabled incompatible con .docx/.xlsx, CRC incorrecto, datos truncados y límites excedidos.

El perfil de directorio requiere EOCD clásico, no multidisco, prefix autoextraíble o bytes posteriores al contenedor; rechaza contadores/dimensiones de directorio que exigen EOCD ZIP64. Los extras de cabecera local los maneja zipfile y **no se afirma rechazo exhaustivo de cualquier variante local ZIP64**. Se rechazan cifrado ZIP y métodos BZIP2/LZMA/otros; OOXML cifrado en contenedor OLE tampoco cumple este perfil. Nombres absolutos, dot-segments, backslashes, controles/NUL, colisiones exactas/casefold, symlinks y archivos especiales se rechazan sin extraer nada.

Estas restricciones pueden rechazar variantes legítimas poco habituales: PDFs con prefijo, trailers inusuales o referencias no reconocidas por el perfil, imágenes con estructuras especiales, OOXML cifrado, directorio ZIP extendido, partes principales en rutas no convencionales o documentos grandes. No se clasifican automáticamente como malware. Es imprescindible corpus QA antes de integrar; no relajar a aceptación por extensión si hay incompatibilidad.

Las [estructuras mínimas WordprocessingML](https://learn.microsoft.com/en-us/office/open-xml/word/structure-of-a-wordprocessingml-document) y [SpreadsheetML](https://learn.microsoft.com/en-us/office/open-xml/spreadsheet/structure-of-a-spreadsheetml-document) sirven de referencia para partes principales y vínculos. El [estándar PNG](https://www.w3.org/TR/png/) define chunks/parámetros; las comprobaciones seleccionadas no implementan toda la norma. Las reglas PDF/JPEG son un perfil operativo limitado, no una certificación de conformidad ISO ni sustituto de sus decodificadores.

## OOXML: presupuestos y coste real

La preinspección del EOCD y directorio cuenta también **registros observados** y verifica tamaños/offsets antes de que ZipFile construya ZipInfo para todo el archivo. Así no se confía en un conteo EOCD pequeño falsificado para permitir un índice masivo. Se conserva la lectura normal con zipfile para validar el contenedor; el preflight no reemplaza su implementación.

Se examinan los metadatos de cada miembro antes de abrirlo. Luego se leen todos los miembros en bloques de hasta64KiB para comprobar CRC y bytes observados, sin escribir archivos, resolver vínculos, abrir recursos externos o inspeccionar contenedores anidados. Se rechaza por tamaño declarado **y por bytes realmente obtenidos**, usando el menor presupuesto restante para cada read. Todos los streams/ZipFile se cierran mediante context managers ante éxito/error.

Sólo las partes obligatorias de metadatos/principal se entregan a Expat. Se acumula una parte XML hasta su límite, se parsea una vez, se descarta el parser y se conservan resúmenes mínimos. La [API Expat](https://docs.python.org/3/library/pyexpat.html) permite callbacks que rechazan DOCTYPE, declaraciones de entidad y referencias externas, incluso con UTF-16; no se basa esa defensa en buscar cadenas de bytes con regex. Se limita profundidad, número global de nodos y atributos por elemento. No hay expansión de entidades ni descarga de schemas.

| Variable / control | Valor predeterminado | Alcance |
|---|---|---|
| MAX_UPLOAD_BYTES, existente | Código20MiB; Compose25MiB =26214400 bytes | Se conserva exactamente el límite previo y lectura máximo+1; no se cambia tamaño de documentos admitidos por configuración |
| DOCUMENT_INSPECTION_ENTRIES | 2048 entradas | EOCD, registros observados e índice ZIP; no 0=ilimitado |
| DOCUMENT_INSPECTION_DIRECTORY_BYTES | 4194304 bytes =4MiB | Directorio antes de ZipFile; limita índice/strings de metadata |
| DOCUMENT_INSPECTION_EXPANDED_BYTES | 104857600 bytes =100MiB | Suma declarada y observada de miembros del contenedor exterior |
| DOCUMENT_INSPECTION_MEMBER_BYTES | 33554432 bytes =32MiB | Cada miembro declarado/observado |
| DOCUMENT_INSPECTION_XML_BYTES | 8388608 bytes =8MiB | Por parte XML interpretada, no por todo el árbol Office |
| DOCUMENT_INSPECTION_XML_NODES | 100000 nodos | Contador compartido entre las partes XML seleccionadas |
| DOCUMENT_INSPECTION_XML_DEPTH | 64 niveles | Máxima profundidad de esas partes |
| DOCUMENT_INSPECTION_IMAGE_RECORDS | 4096 registros | Chunks PNG y segmentos JPEG antes del primer scan |
| XML attrs | 64 atributos por elemento | Se comprueba después de que Expat tokenice el elemento |
| PDF tail | 4096 bytes | Ventana final de reconocimiento startxref/EOF, sin parsing de objetos |

Las ocho variables nuevas se exponen en el anchor Compose, sin tocar valores SS-03/SS-04/SS-10/SS-11 ni MAX_UPLOAD_BYTES. Son cuotas conservadoras de inspección, no capacidades medidas de la infraestructura. Los fixtures existentes eran diminutos y no representaban volumen institucional. Los presupuestos deben calibrarse con documentos QA legítimos antes de desplegar; no se presupone RAM/CPU/disco disponible.

El límite total de archivo no equivale a un límite de body multipart/proxy: FastAPI puede recibir/spoolar antes de entrar en store_version. Nginx versionado no declara un client_max_body_size específico para estos documentos; debe verificarse su política efectiva y overhead en QA. No se modifica Nginx ni la recepción global en esta intervención.

## MIME canónico y cabeceras del cliente

Después de superar el perfil se usa una tabla fija:

| Extensión | MIME persistido del servidor |
|---|---|
| .pdf | application/pdf |
| .docx | application/vnd.openxmlformats-officedocument.wordprocessingml.document |
| .xlsx | application/vnd.openxmlformats-officedocument.spreadsheetml.sheet |
| .jpg / .jpeg | image/jpeg |
| .png | image/png |

El Content-Type del cliente se normaliza sólo para comparar el tipo base; sus parámetros no se guardan ni ejecutan. Se aceptan ausente/vacío, application/octet-stream y binary/octet-stream si el contenido cumple el perfil. application/zip y application/x-zip-compressed sólo son genéricos aceptados para DOCX/XLSX que ya superaron la inspección. Aliases limitados: application/x-pdf, image/jpg, image/pjpeg e image/x-png. Todos se convierten al MIME canónico anterior.

Una inconsistencia manifiesta, por ejemplo PDF con text/html o image/png declarado, produce422. El MIME no determina el detector ni se usa para saltar la comprobación de contenido. No se admiten nuevas extensiones ni se permite ZIP genérico mediante un MIME Office.

La validación se inserta después de autorización de captura, nombre/extensión y límite existente, **antes de la fase de búsqueda de versiones, escritura y persistencia**. Las comprobaciones de autorización previas sí consultan DB en la aplicación real; las pruebas de frontera las sustituyen por dobles y no deben interpretarse como que toda solicitud rechazada evita cualquier acceso a DB o parsing multipart.

## Descarga y versiones históricas

Se conserva db.get(version), 404 si no existe, require_document_access para cada descarga y safe_version_path. Continúa attachment con el nombre original saneado por la carga; no se modifica la política de acceso por vínculo, el acceso a versiones anteriores o las bajas lógicas.

Cabeceras/control nuevos:

```text
Content-Type: application/octet-stream
Content-Disposition: attachment; filename=...  (construido por FileResponse)
X-Content-Type-Options: nosniff
Cache-Control: private, no-store
```

La API no puede distinguir una fila histórica con application/pdf de una recién reconocida sin un marcador de procedencia. Se elige MIME binario conservador **también para las nuevas versiones**, aunque su metadata guardada sea específica: es control del servidor y evita inferir validación a partir de un dato antiguo del cliente. No se releen/reparsean documentos históricos en cada descarga ni se incrementa ese coste para lectores. No se reescribe tipo_mime existente ni se altera SHA/archivo/historial.

La [documentación de FileResponse](https://starlette.dev/responses/#fileresponse) permite MIME, filename y content_disposition_type explícitos. Las pruebas comprueban esos argumentos/cabeceras con dobles, no una respuesta HTTP real. private,no-store evita autorizar almacenamiento nuevo en caches compatibles; no borra descargas/caches históricas ni gobierna un proxy que sobrescriba cabeceras.

Compatibilidad observada: frontend-ssalfer/js/api/documentos.js publica la URL de descarga y el cuerpo/nombre permanecen iguales. El cambio de MIME de descarga es intencional y documentado; debe probarse el comportamiento de navegadores/aplicaciones institucionales, descarga/range y cualquier visor externo. No se promete preview inline, que ya estaba fuera del contrato attachment.

Etapa posterior: añadir, mediante diseño/migración nueva autorizada, un registro de evaluación asociado al SHA exacto, perfil/motor/versiones, fecha y estado de aprobación/cuarentena. Sólo una versión con procedencia verificable puede volver a ofrecer MIME específico en descarga bajo la política aprobada. La revisión de históricos debe ser independiente, acotada y auditable, sin reescribirlos automáticamente ni declarar confiables por fecha o MIME.

## Integridad y controles que permanecen

Los bytes recibidos se almacenan sin modificación; SHA-256 se calcula sobre el original. No hay recomposición de imágenes, normalización Office o sanitización PDF que cambie firmas/valor jurídico. La extensión permitida, nombre saneado, UUID/ruta por versión, verificación bajo upload_root y tamaño se conservan. La numeración concurrente, transacciones y compensación siguen exactamente como antes: SS-12 permanece pendiente.

Los roles captura admin/operador y lectura de los cuatro roles permanecen; access.py no cambia. La lógica de documento compartido que acepta un vínculo legible no se rediseña ni se presenta como resuelta: SS-05 sigue su propio alcance. No se alteran migraciones, modelos, schemas, sesiones o auditoría funcional; sólo el MIME de **nuevas** DocumentoVersion se obtiene del servidor.

## Pruebas ejecutadas

Suite final:

```sh
python3 -B -m unittest discover -s tests/security -p 'test_*.py' -q
# Ran 156 tests; OK (skipped=3)
# 153 aprobadas; 28 nuevas SS-06 aprobadas
```

Los datos son sintéticos y pequeños: PDF mínimo con xref/trailer (590 bytes), PNG1x1 (69), JPEG baseline gris1x1 (137), DOCX mínimo (803) y XLSX mínimo (1320). /usr/bin/file --brief --mime-type - identificó respectivamente application/pdf, image/png, image/jpeg y los MIME OOXML canónicos. Sólo se enviaron esos bytes sintéticos por stdin a una herramienta local ya instalada, con PATH/LC_ALL mínimos y timeout; no hubo red ni ficheros institucionales. Identificación libmagic **no prueba renderizado/decodificación o ausencia de malware**, y la aplicación no la invoca.

| Requisito | Evidencia aislada | Limitación |
|---|---|---|
| PDF válido de fixture / texto-HTML renombrado | Perfil de fixture aceptado; texto/HTML, cabecera sola, falta EOF/xref, offset fuera y truncamiento rechazados | No parser semántico; hay prueba que permite un objeto final sin comprobar tipo XRef |
| PNG/JPEG | Firmas/estructura fixture aceptadas; CRC/longitudes/dimensiones/truncamiento/cabecera arbitraria rechazados | No pixels/entropía; IDAT no-zlib con CRC correcto pasa y se prueba como limitación |
| DOCX/XLSX | Transitional/Strict, ZIP_STORED/DEFLATED, partes/tipos/relaciones y hojas internas | No esquema completo Office ni renderizado |
| ZIP genérico / formato cruzado | Rechazo de ZIP sin partes y de DOCX↔XLSX | No implica desarme de archivos compatibles maliciosos |
| Vacíos / tamaño | 413 y lectura máximo+1 conservada | No prueba body parser ni límite efectivo Nginx |
| MIME | Genéricos/aliases aceptados con canon; incompatibles rechazados | Comportamiento de algunos clientes legacy exige QA |
| ZIP/XML presupuestos | Rechazo previo a indexación, conteo EOCD mentiroso, tamaño individual/acumulado declarado y observado, CRC y directorio truncado | Límites bajos en fixtures, no bombas reales ni estrés |
| Rutas ZIP / XML externo | Dot-segments, symlink y colisiones casefold rechazados; DTD/entidades UTF-8/UTF-16 rechazadas con open externo bloqueado en la prueba | Sin extracción ni resolución de enlaces; no pentest de parsers nativos |
| MIME persistido | Cuerpo real de store_version con DB simulado, canonical_mime en nueva versión, hash/tamaño/bytes exactos | No persistencia PostgreSQL real |
| Descarga | Canon binario, attachment/nosniff/cache, MIME histórico malicioso ignorado y fila no mutada | FileResponse/headers simulado; navegador/proxy pendiente |
| Acceso | La llamada de autorización precede read/validación; captura/read conservados; 403/404 preservados | No se reproducen roles/joins en DB; funciones de acceso intactas por hash/AST |
| Integridad de versiones | Duplicado409, escritura/hash/nombre/número y rollback/compensación originales con dobles | No carrera concurrente ni remediación SS-12 |
| Regresiones previas | 125 pruebas previas aprobadas; tres nativas anteriores omitidas | No equivale a suites integradas institucionales |

Las pruebas importan sólo el módulo stdlib y fixtures puros; extraen por AST funciones específicas de carga/descarga con modelos/Session/Request/FileResponse simulados. No ejecutan imports/top-level del engine/app ni conftest. La lectura y escritura de prueba usan un TemporaryDirectory propio eliminado al finalizar. El contenedor OOXML no se extrae, no hay subprocesos en el validador, no se emplea malware real, y los rechazos no incluyen bytes/nombres/datos del archivo en su detalle público.

### Fixtures originales actualizados, sin cambiar assertions

Se encontraron tres tests de integración que subían sólo b'%PDF-...' sin estructura: test_documents_dashboard.py, test_document_targets_039.py y test_frontend_read_models.py. Esos datos deben rechazarse con el nuevo perfil. Se cambió únicamente su construcción a minimal_pdf del helper puro backend/tests/_document_samples.py, conservando expectativas de permisos, SHA, duplicados, versión vigente y descarga. En el caso de dos versiones se mantiene contenido distinto por etiqueta para no alterar la deduplicación.

Esas suites no se ejecutaron ni se importaron, pues conftest requiere/importa aplicación y DB de prueba autorizada. Se verificó sintaxis y se ejercitaron los fixtures mediante la suite aislada, sin PostgreSQL. No se dejan intencionalmente fixtures inválidos para aparentar que el test de aceptación de un PDF valida el formato.

Omitidas: suites PostgreSQL documentales/read models, TestClient/Starlette reales, navegador, corpus Word/Excel/PDF e imágenes institucionales de QA, decodificadores, antivirus/CDR y ensayos de recursos bajo contención. Las tres omisiones automáticas de unittest son pruebas nativas SQLAlchemy/psycopg2 de SS-10; no se presentan como pruebas nativas documentales ejecutadas.

## Riesgos residuales separados

- **Macros/contenido activo/embebidos:** el MIME principal macro-enabled incompatible con DOCX/XLSX se rechaza, pero binarios VBA/OLE u objetos ocultos en un paquete que cumple el perfil no se analizan ni eliminan. Enlaces externos auxiliares se conservan sin resolverlos. No se declara «sin macros».
- **JavaScript PDF y acciones:** no se inspeccionan objetos/acciones/formularios, adjuntos, launch, contenido remoto ni cifrado. Un PDF peligroso puede tener cabecera/xref/EOF normales.
- **Malware estructuralmente válido:** ninguna firma, CRC o raíz XML detecta por sí sola malware. El hash sólo identifica bytes; no acredita autor o benignidad. Tampoco se valida criptográficamente firma digital/certificado del documento.
- **Políglotas:** se rechazan algunos prefijos/trailers obvios, pero un atacante puede construir contenidos que cumplan varios perfiles o escondan payload dentro de streams/metadata/partes. No hay garantía universal contra políglotas.
- **Integridad profunda:** CRC correcto puede acompañar IDAT/entropía/worksheet XML no interpretable. Se mantiene una prueba positiva de ese límite para no confundir reconocimiento con validación completa. Errores internos pueden aparecer al abrirlo con un cliente real.
- **Descompresión/parsing complejo:** se leen hasta100MiB por OOXML, se tokeniza XML acotado y se mantienen metadatos en memoria. zipfile/zlib/Expat siguen procesando entrada no confiable en el proceso API; versiones/parches, memoria nativa y fallos del parser no quedan aislados por estos contadores. Contenedores anidados no se expanden ni analizan recursivamente.
- **Disponibilidad:** store_version es async pero inspección/CRC/XML/hash/escritura son trabajo síncrono; pueden ocupar event loop y mantener contexto/conexión DB de autorización. No hay deadline duro, cgroups ni cuota global de inspecciones simultáneas. No se introduce un hilo improvisado ni se cambia la transacción de versiones. Requiere worker y presupuestos medidos.
- **Memoria y límites de entrada:** el archivo ya se lee íntegro hasta el límite previo; BytesIO, buffer XML y objetos Expat tienen sobrecoste. El máximo por archivo/parte no es un límite RSS de toda la API. Un cliente puede consumir recursos del parser multipart antes de la validación del servicio; entrada/proxy/rate limiting deben verificarse aparte.
- **Versiones históricas:** siguen pudiendo contener cualquier contenido que se aceptó antes. Se sirven como binario privado, no como «aprobadas»; no se revalidan ni desinfectan. Descargarlas y abrirlas puede ejecutar funciones de la aplicación cliente.
- **SS-05/SS-12 y almacenamiento:** compartir permisos, numeración concurrente, TOCTOU del path/FileResponse, atomicidad DB/archivo y huérfanos conservan sus condiciones anteriores. No se anuncian resueltos por esta validación.

La [guía OWASP de carga de archivos](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html) recomienda combinar tipos/firmas, almacenamiento y controles de contenido; no tomar Content-Type o cabeceras como prueba única de seguridad. Los [riesgos de descompresión zipfile](https://docs.python.org/3/library/zipfile.html#decompression-pitfalls) sustentan presupuestos previos y observados; no proporcionan aislamiento del proceso por sí mismos.

## Recomendación posterior: cuarentena y worker documental

Diseñar un worker por trabajo, separado de API, sin credenciales de DB/sesiones, UID no privilegiado y filesystem privado con entrada read-only. Mantener bloqueado el acceso a red del parser y montajes ajenos, limitar RAM/CPU/PID/disco/tiempo, cancelar/recolectar el trabajo completo y validar una salida de metadatos acotada vinculada al SHA original. Reutilizar los criterios del diseño SS-02 etapa2, sin conceder al parser facultades de backend o administración Docker.

Incorporar parsers/decodificadores mantenidos para PDF/imágenes/OOXML, antivirus con actualización controlada y, según política institucional, CDR. No enviar expedientes a servicios externos sin autorización. Registrar estado de cuarentena/evaluación por hash con versiones de motor/definiciones/perfil, resultados y actor/fecha. Distinguir «recibido», «formato reconocido» y «aprobado para entrega»; un fallo debe permanecer en cuarentena, sin publicar un éxito silencioso.

Esa etapa exige diseño de esquema/contratos/UX y autorización independiente antes de imponer retención de descarga o reclasificar históricos. No modificar la política de vínculos SS-05 como efecto lateral. Si CDR produce bytes distintos, conservar el original inmutable y crear derivado/versionado explícito con procedencia: no sobrescribir un documento firmado ni afirmar que su firma original sigue validando el derivado.

## Aceptación requerida en QA desechable

1. Ejecutar pruebas nativas de documentos, targets y read models en PostgreSQL QA autorizado, verificando upload201, MIME canónico persistido, bytes/SHA, duplicado409 y rollback/cleanup sin alterar permisos o eventos. Ensayar cuatro roles y documentos compartidos sólo según la política vigente.
2. Usar corpus legítimo sintético/QA autorizado: PDF incremental/linealizado/firmado/cifrado, PNG profundidades/interlace/ancillary, JPEG baseline/progresivo/Exif, DOCX/XLSX Strict/Transitional con imágenes/tablas/gráficos/firmas y tamaños reales. Clasificar falsos rechazos del perfil antes de decidir nuevas capacidades; no aceptar por extensión para evitarlos.
3. Comprobar HTTP FileResponse real: attachment con nombre saneado/Unicode, MIME binario uniforme, nosniff y private,no-store en200/206, y tras proxies. Probar descarga nueva/histórica, 404/403, enlaces SSALFER y apertura por aplicaciones aprobadas. No afirmar que nosniff impide toda ejecución al abrir un archivo descargado.
4. Medir tiempo/RSS/CPU/latencia/event loop y uso de conexiones durante inspecciones acotadas/concurrentes en un sandbox desechable. Ajustar cuotas, proxy/body multipart, worker y rate limiting con esos datos; no realizar estrés institucional.
5. Inventariar versiones y parches reales de Python/Expat/zlib, controles del contenedor y ACL/retención de almacenamiento. Probar fallos y límites con datasets sintéticos pequeños; pruebas más hostiles requieren aislamiento fuerte independiente.
6. Aprobar el flujo de cuarentena/AV/CDR y la procedencia de evaluación antes de habilitar MIME específico por versión o revisar históricos. Revisiones/migraciones de datos se autorizan por separado; esta entrega no las realiza.

## Archivos modificados y patch exclusivo

| Archivo | Cambio |
|---|---|
| backend/app/services/documents.py | Validación antes de la fase de versión/escritura y MIME canónico nuevo |
| backend/app/routers/documents.py | Descarga binaria conservadora y cabeceras seguras |
| backend/app/services/document_validation.py | Nuevo: reconocimiento y presupuestos acotados |
| docker-compose.yml | Ocho variables de inspección, sin alterar correcciones previas |
| backend/tests/_document_samples.py | Nuevo: fixtures mínimos stdlib |
| backend/tests/test_documents_dashboard.py | Sólo fixture PDF e import del helper |
| backend/tests/test_document_targets_039.py | Sólo fixture PDF e import del helper |
| backend/tests/test_frontend_read_models.py | Sólo fixtures PDF distintos por versión e import |
| tests/security/test_document_validation.py | Nuevo: 28 pruebas aisladas |
| docs/security/SS-06-ETAPA1-CORRECCION-2026-10-28.md | Nuevo: este informe |
| docs/security/SS-06-ETAPA1-CORRECCION-2026-10-28.patch | Nuevo: diff exclusivo |

El patch compara contra los snapshots locales **anteriores a SS-06**, comprobados por SHA, no contra el árbol HEAD sin correcciones. Así no mezcla los cambios previos del Compose ni reescribe SS-01/02/03/04/10/11. Incluye los tres archivos nuevos de implementación/fixtures/pruebas y este informe; no se incluye a sí mismo. No debe aplicarse como sustituto de las remediaciones anteriores.

Comprobaciones: git diff --check, AST/YAML sin interpolación de .env y git apply --reverse --check --whitespace=error-all, sin aplicar ni revertir el parche. Hashes finales de implementación/pruebas:

| Archivo | SHA-256 |
|---|---|
| backend/app/services/documents.py | `a78f36cf21be48b03526741f5b5f4f7cdb9fa469d7def62b15597248eb386c9b` |
| backend/app/routers/documents.py | `2ad8106a2c6b94384b633efc01555457e5222179b4b3644617c14a85e6372e56` |
| docker-compose.yml | `c8ff985a99895e92ee3b8189fe96a83e7e353fe1e7af383d7a4841ec3514e0b6` |
| backend/tests/test_documents_dashboard.py | `09667044b9fe5f6f2ceaa4a55c532d2d409ef08c122dabd943c0ae32a1bfee09` |
| backend/tests/test_document_targets_039.py | `71627685a865ed5701f6f09807505b8b8b871e671b3c8eca31b6ba14c9360265` |
| backend/tests/test_frontend_read_models.py | `22cb1fedc535fefda07f2156b05944ca16e7b8d6f507bfa9e47629107e035b68` |
| backend/app/services/document_validation.py | `ca81df595d85419406d7f7a00ad6a90499ff1bbc1dfd332cdb5d249f3f6a277c` |
| backend/tests/_document_samples.py | `2f65ec5f698d0f639e9eaa887b73f5ccae824394b27c1b2e153795be662f37ad` |
| tests/security/test_document_validation.py | `89abfe5e512d455b1cb2dba269e7994c9963fd7afb2d0521831e7ffce70268ad` |

El [diff completo y revisable](SS-06-ETAPA1-CORRECCION-2026-10-28.patch) contiene exactamente esta intervención. Extracto de los dos puntos de integración en archivos preexistentes:

```diff
diff --git a/backend/app/services/documents.py b/backend/app/services/documents.py
--- a/backend/app/services/documents.py
+++ b/backend/app/services/documents.py
@@ -13,6 +13,7 @@
 from .. import models, schemas
 from .access import require_document_access, require_document_target_access
 from .common import apply_update, commit_or_conflict, mark_inactive, set_audit_context
+from .document_validation import DocumentValidationError, validate_document
 
 
 ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".jpg", ".jpeg", ".png"}
@@ -162,6 +163,11 @@
     content = await upload.read(MAX_UPLOAD_BYTES + 1)
     if not content or len(content) > MAX_UPLOAD_BYTES:
         raise HTTPException(status_code=413, detail="Archivo vacío o demasiado grande")
+    try:
+        canonical_mime = validate_document(content, extension, upload.content_type,
+            max_file_bytes=MAX_UPLOAD_BYTES)
+    except DocumentValidationError as exc:
+        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc
     digest = hashlib.sha256(content).hexdigest()
     previous = db.query(models.DocumentoVersion).filter(
         models.DocumentoVersion.id_documento == document_id,
@@ -189,7 +195,7 @@
         tamano_bytes=len(content),
         nombre_original=original,
         ruta_almacenamiento=str(relative),
-        tipo_mime=upload.content_type,
+        tipo_mime=canonical_mime,
         id_usuario_carga=user.id_usuario,
     )
     db.add(version)
diff --git a/backend/app/routers/documents.py b/backend/app/routers/documents.py
--- a/backend/app/routers/documents.py
+++ b/backend/app/routers/documents.py
@@ -8,6 +8,7 @@
 from ..database import get_db
 from ..services import documents as service
 from ..services.document_read_models import consolidated_documents
+from ..services.document_validation import download_media_type
 from ..services.access import (
     require_document_access,
     require_document_target_access,
@@ -194,7 +195,9 @@
     return FileResponse(
         service.safe_version_path(version),
         filename=version.nombre_original,
-        media_type=version.tipo_mime or "application/octet-stream",
+        media_type=download_media_type(),
+        content_disposition_type="attachment",
+        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"},
     )
 
 
```

**Intervención detenida para revisión técnica.** No se inicia worker/antivirus/CDR ni otra remediación, no se modifica producción y no se integra o despliega esta corrección.
