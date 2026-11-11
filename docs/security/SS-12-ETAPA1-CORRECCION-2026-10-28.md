# SS-12 etapa 1 — Publicación documental exclusiva y recuperación conservadora

Fecha: 2026-10-28. Software-PA / SSALFER, rama dev, HEAD `683ff75613768de28a7127c7e33a6e2ef4fc40ff`, más remediaciones locales SS-01/02/03/04/06/10/11.

## Dictamen y límites de esta entrega

**Implementación local parcial validada sobre el filesystem de pruebas; SS-12 permanece abierto.** Se sustituye la escritura directa del archivo final por staging privado, escritura exclusiva, fsync y comprobación SHA-256 por descriptor, seguida de publicación mediante hard link exclusivo sin reemplazo. La compensación **nunca elimina un nombre publicado**, incluso si falla commit, rollback, refresh o la respuesta HTTP. Se limpian únicamente entradas conocidas del staging de la operación cuando su identidad coincide.

**No se ofrece atomicidad entre PostgreSQL y filesystem, ausencia de huérfanos, protección contra un host/UID comprometido ni numeración serializada ya demostrada.** No se implementa el bloqueo padre mientras no exista QA PostgreSQL para validar transacciones/orden de locks. Se mantienen max(numero_version)+1 y las restricciones únicas existentes; una carga legítima concurrente aún puede terminar en409. No hay mutex por proceso ni retry automático.

La descarga conserva íntegramente safe_version_path y FileResponse de SS-06. **El TOCTOU de descarga no se declara corregido.** Se prepara una prueba nativa que puede documentar la sustitución del path y otra de headers; ambas quedaron omitidas por falta de Starlette. La alternativa de descriptor necesita validación real del framework antes de integrar.

Resultado final de la suite aislada: **182 pruebas descubiertas, 177 aprobadas y 5 omitidas**. Se aprobaron24 nuevas SS-12 y las153 anteriores, incluidas las28 de SS-06. Las omisiones son tres nativas previas de SS-10 y dos nuevas de Starlette. **Seis pruebas PostgreSQL QA adicionales fueron preparadas pero no ejecutadas ni importadas**. Los procesos hijos utilizados en pruebas sólo manipularon pequeños archivos sintéticos propios; no hubo conexión a servicios.

No se accedió a producción/servidor institucional, leyó .env, instaló software, ejecutó Docker/migraciones, modificó documentos reales o realizó commit/push/merge/despliegue.

## Inspección y estado previo

Se inspeccionaron services/documents.py, routers/documents.py, document_validation.py de SS-06, Documento/DocumentoVersion, restricciones y trigger de inmutabilidad de la migración001, pruebas documentales/rollback, conftest, volúmenes/UPLOAD_ROOT y los informes SS-12. SQLAlchemy, psycopg2, FastAPI y Starlette siguen ausentes en el Python local; no se intentó suplirlos instalando paquetes o utilizando un servicio real.

El estado inicial coincide con dev/HEAD de referencia y contiene todas las remediaciones anteriores sin integrar. Se tomaron snapshots/hashes sin leer .env. Sólo cambian dos archivos preexistentes de este alcance: store_version dentro de services/documents.py y el adaptador/expectativa correspondiente de su prueba SS-06. Validador SS-06, router de descargas, access.py, modelos, schemas, migraciones, configuración del engine, Compose y frontend permanecen intactos.

Restricciones declaradas existentes, sin duplicarlas ni alterarlas:

| Restricción | Garantía declarada |
|---|---|
| uq_documento_version | UNIQUE(id_documento,numero_version) |
| uq_documento_hash | UNIQUE(id_documento,hash_sha256) |
| uq_documento_ruta | UNIQUE(ruta_almacenamiento) |
| chk_documento_version | Número positivo y tamaño no negativo |
| fn_documento_version_inmutable | Rechaza UPDATE/DELETE de versiones |

Su definición está comprobada como texto en modelo/migración. **Su aplicación efectiva, privilegios y semántica bajo concurrencia no se inspeccionaron en un servidor**; las pruebas QA preparadas la verifican posteriormente.

## Escenarios de carrera: evidencia y estado

| Escenario | Estado de evidencia | Control implementado / pendiente |
|---|---|---|
| Dos cargas distintas al mismo documento calculan el mismo max+1 | Confirmado por secuencia de código; PostgreSQL real pendiente | No se serializa aún. Unicidad declarada es última defensa,409 posible; protocolo con fila padre se diseña más abajo |
| Dos cargas de los mismos bytes | Lookup SHA existente no coordina solicitudes; uniqueness declarada | Duplicado observado temprano409; carrera entre lookup/commit pendiente QA. No se reintenta ni se crean dos números confirmados por una garantía nueva del código |
| Dos publicadores intentan el mismo nombre final | Confirmado por dos threads y dos procesos Python independientes en filesystem local | os.link no reemplaza; uno publica y el otro obtiene colisión controlada; bytes completos de uno solo |
| Escritura corta o parcial | Confirmado por escrituras parciales reales y cero-write/error simulado | Se completa en bucle acotado; el nombre final todavía no existe; readback/tamaño/SHA antes de publicar |
| Disco lleno, permiso denegado, fallo fsync/read | Simulación de errno y cancelación, sin fallo físico del disco | Limpieza de staging propio cuando es posible,507 controlado en IO; no publicación parcial ni copy fallback |
| Fallo después de link y antes del registro/commit | Reproducido con excepción y os._exit de hijo en la fase de filesystem | Se conserva el archivo final. Puede quedar huérfano; no se barre ni elimina automáticamente |
| COMMIT confirmado en servidor pero respuesta perdida | Riesgo real del protocolo, simulado con doble que marca commit y lanza excepción | Nunca unlink final;409 indica resultado no confirmado e invita a consultar historial. No se afirma reproducido en PostgreSQL real |
| COMMIT exitoso seguido de refresh/HTTP fallido | Simulado con doble; HTTP real pendiente | Archivo publicado permanece, sin retry automático |
| Cancelación durante write/fsync/commit | BaseException inyectada en esos puntos y pruebas de cierre | Staging propio cerrado; publicado conservado. IO/SQL síncronos pueden no reaccionar de inmediato a una desconexión real |
| Terminación abrupta del proceso | os._exit(17) real en hijos sintéticos, sin finally | Se observan staging parcial, staging completo y publicación sin registro. Es una demostración de ventanas residuales, no fallo eléctrico de host |
| Sustitución de payload/directorio | Reproducida localmente en rutas sintéticas propias | Comprobaciones nofollow/identidad rechazan la sustitución observada y no eliminan entradas ajenas; no se promete resistencia absoluta a un actor con el mismo UID/root |
| Archivo cambiado después de safe_version_path y antes de FileResponse | Código/path reopening identificado, Starlette real ausente | Implementación intacta; prueba nativa pendiente y diseño de descriptor, sin afirmar filtración reproducida |
| Varias instancias compartiendo volumen | Dos procesos locales prueban exclusión FS, no PostgreSQL/FS distribuido | Requiere mismo almacenamiento físico, UID/ACL y semántica de hard links/fsync; QA NFS/CIFS/multihost pendiente |

## Implementación del almacenamiento

Nuevo módulo document_storage.py, sin DB, red, shell ni ejecución de herramientas. Trabaja con bytes originales ya autorizados/reconocidos por SS-06.

1. Abrir la raíz canónica configurada mediante descriptores de directorio, recorriendo componentes con O_DIRECTORY/O_NOFOLLOW/O_CLOEXEC. Rechazar raíz del sistema, dot-segments y plataformas sin esas banderas. El servicio conserva upload_root(), que resuelve la raíz **administrada** configurada; esa configuración y sus ancestros son una frontera de confianza, no una ruta del cliente.
2. Abrir/crear el directorio numérico del documento sin seguir symlinks. Rechazar root/directorio documental escribibles por cualquiera. No cambiar permisos de carpetas históricas ni asumir que una variable demuestra ACL correctas.
3. Crear exclusivamente .pending-UUID (0700) y payload (O_CREAT|O_EXCL,0600). Si el nombre ya existe no se adopta, reutiliza o borra. No hay búsqueda/limpieza global y no se elimina el directorio documental, que puede servir a otra solicitud.
4. Escribir por fd en bloques de hasta64KiB, atendiendo short writes y rechazando cero-write. fsync del archivo, lectura por el mismo fd con conteo acotado y SHA-256/tamaño exactos. Se conserva todo byte del original, incluido formato/MIME de SS-06; no se transforma ni se recodifica.
5. Generar el nombre final con el número calculado y el mismo UUID servidor de la operación: numero-UUID.ext. El patrón admite las mismas extensiones y nunca usa el nombre del cliente como ruta. La correlación de operación permite asociar un evento seguro con el sufijo del archivo sin registrar documento/usuario/path en logs.
6. Comprobar directorio/payload regulares y sus dev/inode. Publicar con os.link entre staging y directorio final por dir_fd, follow_symlinks=False. El hard link crea el nombre final de forma exclusiva; **no se usa os.replace/rename que sobrescriba**, ni exists+write, ni copy ante EXDEV. Verificar la identidad de la nueva entrada y fsync de los directorios documental/raíz antes de intentar registrar la versión.
7. Al salir, unlink sólo del payload creado por esta operación si la identidad sigue coincidiendo; rmdir sólo del staging identificado y vacío. Mantener el fd de directorio hasta terminar esa comprobación. No hay rmtree ni iteración de directorios, y ningún código de compensación elimina el nombre final.

La [API os.link/dir_fd de Python](https://docs.python.org/3/library/os.html#os.link) permite estas operaciones sin abrir rutas de cliente; sus garantías concretas siguen dependiendo del sistema de archivos. Las pruebas usan Linux local y demuestran exclusión por llamada del sistema, no un mutex Python. Staging y destino están bajo el mismo directorio documental para evitar una publicación cross-filesystem. Si hard links o fsync de directorio no funcionan, se falla de forma explícita; no se degrada silenciosamente a una copia insegura.

Los descriptores se cierran en éxito y error; las pruebas comprueban EBADF después de cerrar los fd propios. Si cleanup falla o hay una entrada desconocida, se conserva el contenido sospechoso y se emite DOCUMENT_STAGING_CLEANUP_INCOMPLETE, sin convertir la limpieza en un borrado de archivos ajenos. Una carpeta vacía de documento puede quedar creada; no se elimina por riesgo de uso concurrente.

### Permisos y sustituciones: límites reales

0700/0600 dan privacidad por UID, **no aislamiento frente a otros procesos con ese mismo UID, root o un administrador del volumen**. Las verificaciones de identidad detectan sustituciones observadas, pero no constituyen compare-and-unlink atómico contra un atacante que puede renombrar entradas justo después del stat, escribir en el mismo inode o cambiar mounts. Los directorios deben estar administrados y protegidos de actores ajenos. Tampoco se garantiza que un directorio canónico no cambie entre comprobación y commit DB.

No se modifican ACL/propietarios de archivos existentes. Nuevas carpetas/archivos privados pueden requerir revisar UID/GID/backup entre contenedores y el host. No aplicar chmod masivo para sortearlo; validar el modelo de servicio. Compose base usa uploads_data y desarrollo un bind mount; el mismo nombre de volumen en **dos hosts** no demuestra almacenamiento compartido. No se ejecutó Docker ni se inspeccionó un mount institucional.

fsync solicita persistencia al kernel/filesystem, no prueba la durabilidad del hardware/NFS/configuración efectiva. El montaje, journaling, coherencia, enlaces y recuperación de backups requieren QA. Los archivos nuevos no son inmutables a nivel de kernel: se evita sobrescritura accidental por este código, no escritura deliberada de un propietario comprometido.

## Secuencia real de store_version en etapa 1

| Fase | Operación y propiedad | Qué puede fallar |
|---|---|---|
| 1 | Autorización de captura, nombre/extensión, límite y validación SS-06; hash original | Se conservan401/403/413/422 y las reglas existentes; sin staging para contenido rechazado |
| 2 | Lookup temprano SHA; si ya existe,409 | No es una coordinación entre solicitudes; puede quedar obsoleto inmediatamente |
| 3 | Staging privado completo +fsync+readback SHA | Sólo entradas propias; sin nombre final ni registro nuevo |
| 4 | Calcular max+1 como antes y preparar ruta servidor | No hay lock padre todavía; una carrera de número sigue posible |
| 5 | Link exclusivo y fsync de directorios | El final ya existe; DB todavía no lo confirma. Puede quedar archivo sin registro |
| 6 | Contexto de auditoría, add y commit de DocumentoVersion | commit hace flush implícito; uniqueness puede fallar después de publicar. No se añade flush o transacción experimental antes de QA |
| 7 | Refresh/retorno y cleanup del staging | Fallo HTTP no implica fallo DB. El final se conserva siempre |

El [comportamiento de flush/commit de SQLAlchemy](https://docs.sqlalchemy.org/en/20/orm/session_basics.html#flushing) no crea una transacción con el filesystem. No se añade un engine, pool ni aislamiento global. La transacción existente de autorización puede seguir abierta durante IO; stage1 no resuelve el coste síncrono en event loop ni conexión retenida.

Ante excepción de registro se intenta rollback y se conserva el archivo publicado. Una excepción normal produce409 con mensaje controlado **«No fue posible confirmar el registro de la versión; consulte el historial antes de reintentar.»**; cancelaciones BaseException se propagan después del rollback. Si rollback falla, su error también se propaga y el final sigue intacto. Un OSError de la capa FS se traduce a error de almacenamiento507; colisiones/política de ruta producen409 y plataforma no soportada503. El frontend conserva el esquema de éxito y los nombres/bytes, pero esos fallos y la precisión del mensaje deben comprobarse en QA.

[COMMIT PostgreSQL](https://www.postgresql.org/docs/15/sql-commit.html) confirma los cambios DB, no la publicación de archivos. Si se pierde la respuesta de la conexión, un rollback posterior no deshace un commit ya confirmado por servidor. **No deducir fracaso de la transacción a partir de la excepción del cliente.** No se consulta/reintenta automáticamente contra otra conexión ni se vuelve a publicar al ver409.

## Cambio explícito respecto a una expectativa de SS-06

La prueba previa de commit fallido exigía que no quedara ningún PDF. Esa compensación era insegura bajo COMMIT incierto. Se cambia **sólo esa expectativa** a conservar un archivo completo con bytes/SHA originales y ningún staging normal; también se inyecta el nuevo helper en el adaptador aislado. No se debilitan las pruebas de formato, MIME canónico, tamaño, autorización o headers. El validador SS-06 y sus presupuestos están idénticos por hash, al igual que el router de descarga.

Todos los demás archivos previos de remediación y sus documentos permanecen sin cambios. Los documentos anteriores describen la entrega histórica; este informe deja trazable por qué su expectativa de borrado en rollback se sustituye en SS-12.

## Diagnóstico seguro

Se reutiliza DiagnosticEvent/ssalfer.diagnostics de SS-10. Sólo se registran códigos constantes (DOCUMENT_STORAGE_FULL/PERMISSIONS/QUOTA/CROSS_DEVICE/SYMLINK/IO, CLEANUP_INCOMPLETE o REGISTRATION_UNCONFIRMED), componente documents y UUID de operación generado por servidor. No se interpolan OSError, path, hash, nombre original, actor, parámetros SQL, cuerpo o cabeceras. La correlación de operación es distinta de la correlación HTTP y no contiene datos de usuario.

La prueba nueva captura el formato final SafeJSONFormatter y comprueba ausencia de nombre/path/sentinela sintético del error. No se insertan eventos de DB para cada fallo de almacenamiento ni se altera auditoría funcional. El registro de diagnóstico no es una bitácora durable de publicación: si el proceso muere antes de emitirlo, puede no existir evidencia suficiente para resolver automáticamente el estado.

## Diseño de serialización PostgreSQL pendiente de validación

**Propuesta, no implementada en store_version.** Usar una fila estable de documento como coordinador, no locks del proceso ni sólo SELECT max. Secuencia para evaluar en QA:

1. Terminar autenticación/autorización inicial y reconocimiento/preparación privada antes de adquirir el lock documental; evitar CPU de inspección bajo un bloqueo largo. La separación de sesiones debe diseñarse expresamente: no empezar otra transacción en una Session que ya ha hecho autobegin sin revisarla.
2. Abrir una transacción de asignación con aislamiento **READ COMMITTED** explícitamente verificado en QA. SELECT del id/activo del documento con FOR UPDATE por PK; proyección mínima/of documento, evitando que eager joins provoquen locks en otras tablas o FOR UPDATE sobre lado nullable de un outer join.
3. Revalidar documento/alcance con la misma política actual, sin ampliar SS-05. Tras adquirir el lock volver a buscar SHA y calcular max+1. La comprobación temprana previa al staging sólo es una optimización, no una decisión definitiva.
4. Insertar/flush de la versión dentro de la transacción para probar constraints antes de publicar. Publicar el staging ya completo y confirmar. Un fallo anterior a publicación deja sólo staging conocido; una publicación seguida de fallo DB conserva la ventana que necesita reconciliación.
5. Mantener orden consistente: autenticación finalizada → un documento padre → inserción/versiones/auditoría. Para operaciones futuras con varios documentos, ordenar IDs. Revisar también FKs a actor y mutadores de catálogo/vínculos/usuarios: **no se afirma ausencia global de deadlocks** por dibujar un orden local. No bloquear relaciones adicionales sin justificación.
6. Locks se liberan por commit/rollback; documentos distintos usan filas distintas. Definir lock_timeout/statement_timeout según mediciones y fallo controlado; ningún retry infinito. Si se autorizan reintentos por40001/40P01, deben reiniciar toda la transacción con idempotencia y límite, nunca sólo repetir max+1 sobre un snapshot antiguo.

[PostgreSQL documenta los row locks y deadlocks](https://www.postgresql.org/docs/15/explicit-locking.html). READ COMMITTED es relevante: con REPEATABLE READ y un snapshot anterior, esperar un lock de una fila que no se actualiza no hace visible mágicamente una versión hija insertada después. Otra alternativa es un contador padre actualizado de forma atómica, pero requiere cambio de esquema/contrato autorizado. No se elige aquí como arreglo improvisado.

FOR UPDATE compite con locks por FK, y un FOR NO KEY UPDATE bien coordinado podría reducir bloqueos si se valida con todos los escritores. No se sustituye automáticamente por una combinación SQLAlchemy no probada. Todas las instancias/escritores deben adoptar el mismo protocolo; durante despliegues mixtos se sigue dependiendo de constraints.

Las restricciones existentes permanecen como última defensa aun con serialización. Revalidarlas contra servidor QA, no asumir que coinciden con el modelo. No se propone duplicarlas ni alterar migraciones históricas.

## Diseño de recuperación y reconciliación — requiere autorización posterior

### Ventanas que no desaparecen

| Punto de caída | Posible estado persistente | Tratamiento conservador |
|---|---|---|
| Durante escritura privada | payload parcial sin final/registro | No lo presenta esta API como versión. Clasificar staging pendiente; no borrarlo sólo por edad |
| Staging completo antes de publicación | Archivo privado completo sin registro | Puede ser trabajo en vuelo o terminado abruptamente; hace falta identidad/lease durable |
| Link efectuado, antes/después de fsync de directorio | Final completo y staging, DB todavía sin registro | No puede inferirse rollback. Durabilidad real depende de FS; conservar candidatos |
| Commit falla de forma conocida o desconocida tras publicar | Final con/sin fila confirmada | Conservar; ausencia en una lectura aislada puede ser una transacción aún en curso |
| Commit confirmado y respuesta perdida | Registro y archivo correctos, cliente no sabe | Consultar historial/operación y verificar por SHA; no borrar ni reintentar a ciegas |
| Caída de almacenamiento / restore desalineado | Fila confirmada sin archivo o bytes distintos | Incidente de integridad/disponibilidad; no borrar histórico ni reutilizar el número |

La política actual favorece conservar evidencia y disponibilidad de una versión potencialmente confirmada sobre eliminar residuos inmediatamente. Puede aumentar la cantidad de archivos publicados sin registro tras conflictos inequívocos; es una limitación deliberada y necesita cuota/monitoreo/reconciliación, no una afirmación de que el huérfano desapareció.

### Bitácora propuesta

Una migración nueva, forward-only y autorizada podría crear una entidad de publicación/trabajo separada de documento_version inmutable. Campos a diseñar: UUID de operación/idempotencia generado por servidor, documento/actor, hash/tamaño/MIME esperado, ruta servidor, número asignado, perfil de validación, estado/fechas, lease/propietario de intento y referencia a la versión confirmada. No guardar contraseñas, sesiones ni cuerpos en la bitácora o logs. Aplicar permisos mínimos, retención y auditoría de decisiones.

Protocolo propuesto:

- Registrar intención durable antes de preparar el archivo. Si falla la confirmación de intención, consultar esa operación antes de crear otro trabajo; no deducir que no existe.
- Preparar archivo bajo identidad de operación con datos validados. Guardar metadatos de fase/lease sin mantener un lock documental durante inspección. Un estado durable puede quedar por detrás del filesystem; no asumir sincronía perfecta.
- Bajo la transacción documental serializada, asignar/flush, publicar y confirmar **versión + estado confirmado de la bitácora en la misma transacción DB**. Así la consulta posterior a un COMMIT incierto puede resolver el estado DB con una lectura nueva del primario; no hace atómica la publicación de FS.
- No actualizar la misma fila de bitácora desde una segunda conexión mientras otra transacción la tiene bloqueada para aparentar un estado «publicado durable»: puede bloquearse a sí misma. Si se necesita un manifiesto FS adicional, especificar orden/fsync y reconciliar las dos bitácoras sin prometer atomicidad.
- Al reiniciar, reconciliar únicamente trabajos propios y terminales, respetando leases/epochs y operaciones activas de otras instancias. Un TTL o mtime antiguo no demuestra que el trabajo terminó. Controlar trabajo máximo/cola/archivos simultáneos con coordinación compartida y cuotas reales.

### Reconciliador propuesto: primero sólo lectura

Construir un inventario privado acotado por lotes de filas/versiones y entradas controladas del volumen; correlacionar operación/ruta exacta, tamaño/hash y, cuando corresponda, identidad de FS. No usar sólo el prefijo de número: dos intentos no confirmados pueden tener el mismo número y distintos UUID.

Clasificaciones de revisión:

- Fila + archivo + hash/tamaño concordantes: consistencia observada en ese instante, sin certificar que un host con privilegios no lo cambie después.
- Archivo publicado sin fila visible: candidato sin referencia, **no huérfano confirmado automáticamente**. Resolver transacciones/bitácora/leases y despliegues en vuelo antes de cualquier decisión.
- Fila sin archivo: incidente; recuperar desde backup íntegro con SHA esperado, conservando versión e histórico. No borrar la fila para «hacer coincidir» el inventario.
- Hash/tamaño discrepantes o entrada inesperada/symlink: incidente/quarantena de revisión; no sobrescribir ni seguir el enlace para completar la operación.
- Staging conocido o entradas ajenas en él: revisar propietario de operación y fase. Nunca rmtree general ni purga por antigüedad en este paso.

La limpieza posterior requiere autorización/política explícita, prueba de inactividad, periodo de retención, trazabilidad y barreras contra carreras. El reconciliador **no se implementa ni ejecuta en esta etapa**. Ningún archivo huérfano institucional fue enumerado o eliminado.

Backups deben coordinar puntos de recuperación DB/volumen, manifiestos de hashes y verificación de restauración. Incluso una bitácora DB no recupera bytes que nunca persistieron físicamente. Probar pérdida de proceso, servidor DB, mount y restauración en QA; no prometerlo a partir de fsync o un try/except.

## Descarga y TOCTOU: diseño, sin cambio de implementación

safe_version_path actualmente resuelve/comprueba el path y FileResponse lo abre después. Cambiar la entrada entre ambos puede cambiar el contenido; no se compara SHA en el camino actual. Se conservan autorización, attachment, application/octet-stream, nosniff y private,no-store de SS-06 exactamente.

Propuesta Linux a validar: abrir raíz/documento/archivo con dir_fd, O_NOFOLLOW/O_DIRECTORY donde corresponda y O_RDONLY/O_CLOEXEC para el archivo; fstat regular; contrastar tamaño y hash mediante el **mismo descriptor** que luego se entrega. No volver a abrir el path tras validar. Usar el fd evita una sustitución del nombre posterior, pero no evita escritura en el mismo inode por un actor con acceso: puede requerirse almacenamiento inmutable o snapshot privado verificado y permisos del volumen.

FileResponse usa path y optimizaciones/rangos del servidor: no se adapta pasando un fd de manera no documentada. Diseñar una respuesta propietaria de descriptor o snapshot y probar con Starlette real: Content-Disposition/encoding, range200/206/416, tamaño, cancelación antes/durante streaming, fallos, cierre, cliente lento y caché. No sustituir el mecanismo actual sin ese ensayo. No reabrirlo después de hashear y llamar a eso protección TOCTOU.

Las dos pruebas nativas preparadas verifican headers y documentan la reapertura por path al sustituir **dos archivos sintéticos propios**. Una prueba de riesgo que pasa no es aceptación de una corrección. En este entorno ambas quedaron omitidas; no se afirma que la reproducción nativa se ejecutó.

## Pruebas ejecutadas y evidencia

```sh
python3 -B -m unittest discover -s tests/security -p 'test_document_storage.py' -q
# 23 pruebas de almacenamiento/servicio aprobadas en esa ejecución intermedia
python3 -B -m unittest discover -s tests/security -p 'test_*.py' -q
# Ejecución final: Ran 182 tests; OK (skipped=5)
# 177 aprobadas, incluidas24 nuevas SS-12 y28 de SS-06
```

La prueba de diagnóstico seguro se añadió después del primer comando; la suite final incluye las24. Las pruebas se inspeccionaron antes de ejecutarlas. Usan TemporaryDirectory propio, datos sintéticos pequeños y módulo puro; los cuerpos de servicio/modelos/DB se aíslan con el adaptador de SS-06. No se importó app.database/app.main ni conftest, ni se ejecutó pytest/collect-only. Linux ejecuta os.open/link/fsync/read/write/unlink/rmdir reales bajo el directorio de prueba; se inyectan errores sólo en los puntos indicados.

| Control | Evidencia ejecutada | Límite |
|---|---|---|
| Privacidad/exclusividad | mkdir exclusivo0700, payload0600 O_EXCL, colisión de archivo/symlink/directorio preservada | FS local; UID/root ajeno no aislado |
| Publicación completa | Durante short writes el final no existe; readback/tamaño/SHA y enlace del mismo inode; link exclusivo | No prueba durabilidad ante pérdida eléctrica |
| Recursos | FD propios dan EBADF tras cierre; staging limpio en caminos ordinarios/error/cancel simulado | Si cleanup es denegado o detecta entrada desconocida se conserva y registra |
| Datos/bytes | Bytes originales y SHA exactos; sin modificación del MIME SS-06 | No hashing nuevo en descarga |
| Fallos | ENOSPC/EACCES/EIO, cero-write, cancel en write/fsync/commit, constructor/hash, fallo de link/EXDEV y fsync posterior | Simulación de errores, no disco/servidor real averiado |
| No borrar ajenos | Fuente sustituida, directorio documental renombrado, entradas desconocidas y link existente | No defensa total ante una carrera hostil del mismo UID entre stat/unlink |
| Concurrencia FS | Dos threads y dos procesos Python independientes, barrera local, un ganador por nombre | No coordinación PostgreSQL ni prueba multihost/NFS |
| Caída de proceso | Tres hijos con os._exit17 en parcial/staged/published dejan estados residuales esperados | No commit PostgreSQL ni caída de host |
| Commit incierto | Doble marca confirmación y lanza; archivo íntegro retenido, rollback intentado,409 sin retry | No fallo real de conexión al servidor |
| Refresh/rollback fallidos | Archivo final retenido y staging liberado | Persistencia real de DB pendiente |
| SS-06 | 28 regresiones aprobadas con única expectativa de compensación corregida y adaptador nuevo | Pruebas HTTP/DB originales no ejecutadas |
| Observabilidad | Captura formateada final sin sentinel/path/errores crudos | No acredita recolectores externos o configuración desplegada |

En la salida final apareció un token controlado document_storage durante un fallo de IO sintético antes de configurar el logger en ese test; no incluyó paths, datos ni excepción. La prueba dedicada sí captura el formatter final versionado y verifica los campos seguros. No se utiliza ese token como bitácora ni se afirma trazabilidad durable por ese log.

### PostgreSQL QA preparado — no ejecutado

Archivo independiente tests/qa/test_document_publication_postgresql.py, **fuera de backend/tests/conftest.py**. Antes de importar el motor requiere SS12_QA_ENABLE=1, APP_ENV=test, SS12_QA_DATABASE y SS12_QA_ALLOW_DATABASE iguales a software_pa_test, host local/lab permitido, puerto/usuario/password/actor QA explícitos. No carga .env ni el engine habitual. Primero consulta identidad de DB/cluster y actor sintético activo; exige cluster_name=ss12-document-disposable antes de crear datos.

Estas guardas son complementarias, **no autorización ni prueba física de que un servidor es desechable**. El operador debe acreditar y autorizar el clon y endpoints. No se leyeron esos valores de conexión ni se ejecutó/importó el archivo en esta intervención. Sólo se verificó su AST.

Seis ensayos preparados:

1. Constraints únicas reales y no diferibles, sin crear/alterar constraints.
2. Dos sesiones: mismo documento bloqueado con NOWAIT, otro documento independiente, liberación por commit/rollback y un único reintento explícito.
3. Protocolo de orden actual con max forzado simultáneo y bytes diferentes: una confirmación y un conflicto, archivos publicados conservados.
4. Mismos bytes: una sola confirmación SHA y409 controlado por unicidad.
5. Protocolo **propuesto** de READ COMMITTED + lock padre + insert antes de publicar: números1/2 para distintos bytes y un rechazo para duplicado.
6. Rollback tras publicación: archivo retenido sin fila confirmada.

Son pruebas nativas de SQL y de un protocolo de referencia expresamente separado de store_version, **no una ejecución nativa del endpoint/RBAC** ni implementación del lock propuesta en producción. Deben complementarse con las suites API documentales del clon autorizado. Sus timeouts3s/1s y barreras5s son valores pequeños de ensayo QA, no configuración operativa de la API.

El runner futuro crea filas sintéticas y usa un TemporaryDirectory propio; no borra filas históricas ni ejecuta migraciones. El clon debe descartarse mediante el procedimiento independiente autorizado después de las pruebas. No trasladar estas guardas a una conexión institucional ni reutilizar sus credenciales.

## Requisitos de aceptación QA y riesgos residuales

- Ejecutar primero las comprobaciones de almacenamiento con filesystem/volumen real de QA y los24 tests nuevos: hard links, fsync de archivo/directorio, mode/UID/GID/ACL, ausencia de fallback inseguro y archivos completos. Probar al menos dos procesos/instancias sobre el mismo mount físico.
- En PostgreSQL desechable autorizado ejecutar el archivo preparado y las suites API reales: confirmar control de número/hash/409 y límites de espera, aislamiento efectivo, locks liberados, distintos documentos, cambios de estado/activos, usuarios y FKs. Verificar que la propuesta no produce deadlocks con mutadores relacionados antes de implementarla.
- Inducir fallo controlado de conexión durante COMMIT en ese clon, resolver estado desde una conexión nueva al primario y comprobar archivo/fila. No usar el test doble como evidencia de que el servidor confirmó o revirtió una transacción real.
- Validar confirmación + pérdida HTTP y cliente que reintenta: sin sobrescritura ni borrado, con recuperación por historial/idempotencia. Probar la nueva respuesta409 de incertidumbre y507 de IO en SSALFER, sin logout/cambios de autorización.
- Ejecutar las dos pruebas Starlette nativas y diseñar/validar la respuesta de descriptor antes de cambiar download. Validar range/cancel/headers y hashes con archivos sintéticos, incluidos lectores autorizados y denegados mediante API real.
- Medir coste de readback/fsync, event loop/Session retenida, RAM/FD/disk y concurrencia. Añadir presupuestos/worker/cola sólo con diseño aprobado; no cambiar el pool global o aplicar sleeps/mutex para ocultar el problema.
- Probar journal/reconciliador propuesto y restauración consistente DB+FS con datos QA antes de autorizar limpieza. **No purga automática de huérfanos en esta etapa.** Los candidatos pueden corresponder a operaciones vivas o commits inciertos.

Siguen pendientes numeración serializada, un protocolo adoptado por todos los escritores, resolución automática de commit incierto, bitácora durable, cuotas/retención/reconciliación, resistencia a fallos de host/volumen y TOCTOU de descarga. Nuevos permisos privados y rechazo de symlinks/world-writable/hardlinks no disponibles pueden descubrir configuraciones legítimas pero incompatibles; revisar sin ampliar permisos de históricos a ciegas. El incremento de huérfanos conservados ante conflictos conocidos es un riesgo de disponibilidad que debe gestionarse con esa segunda etapa.

## Archivos y diff exclusivo

| Archivo | Cambio |
|---|---|
| backend/app/services/documents.py | Sólo store_version: staging/publicación y conservación ante incertidumbre |
| backend/app/services/document_storage.py | Nuevo: primitive de almacenamiento/diagnóstico POSIX |
| tests/security/test_document_validation.py | Adaptador SS-06 y expectativa de compensación justificada |
| tests/security/test_document_storage.py | Nuevo:24 pruebas aisladas, FS local/procesos/dobles |
| tests/security/test_document_starlette_pending.py | Nuevo: dos pruebas nativas omitidas en este entorno |
| tests/qa/test_document_publication_postgresql.py | Nuevo: seis ensayos QA opt-in preparados, no ejecutados |
| docs/security/SS-12-ETAPA1-CORRECCION-2026-10-28.md | Nuevo: informe y diseño de recuperación |
| docs/security/SS-12-ETAPA1-CORRECCION-2026-10-28.patch | Nuevo: diff exclusivo de esta intervención |

El patch compara con snapshots del estado local **antes de SS-12**, no con HEAD sin las correcciones previas. Incluye los cuatro archivos nuevos de implementación/pruebas y este informe; excluye únicamente el patch mismo. Se verifica por git apply --reverse --check --whitespace=error-all y git diff --check, sin aplicar ni revertir nada. No modifica migraciones, restricciones, servicio de validación, router de descarga, Compose, frontend ni otros hallazgos.

| Archivo de implementación/pruebas | SHA-256 final |
|---|---|
| backend/app/services/documents.py | `a9df440899a0d1a121a6821c461a3082204b8bc20d583c80b1cde27700939dc9` |
| tests/security/test_document_validation.py | `341b18e6476ba36fe4db454708e03b4a0221d7aa8955af1e165cb7aca1271f56` |
| backend/app/services/document_storage.py | `4c9f70f526c078c4f4a1fc15729654f1eed7409f30880c378fc90ad46adae541` |
| tests/security/test_document_storage.py | `bc177a4572c2932094fccb5097f87adac3c40ac725c130d246a764ec9d1a39c0` |
| tests/security/test_document_starlette_pending.py | `fccba68a1ccffc4155dd567dd04d4cef8dcea1986d03ac5b814d5093797a620a` |
| tests/qa/test_document_publication_postgresql.py | `2b1f89888c6182acd463915e22ebf696103af56e21256a0f93e04c919684f1dc` |

El [parche completo y revisable](SS-12-ETAPA1-CORRECCION-2026-10-28.patch) contiene exactamente esta intervención. Diff de los archivos preexistentes:

```diff
diff --git a/backend/app/services/documents.py b/backend/app/services/documents.py
--- a/backend/app/services/documents.py
+++ b/backend/app/services/documents.py
@@ -3,7 +3,6 @@
 import hashlib
 import os
 import re
-import uuid
 from pathlib import Path
 
 from fastapi import HTTPException, UploadFile
@@ -14,6 +13,7 @@
 from .access import require_document_access, require_document_target_access
 from .common import apply_update, commit_or_conflict, mark_inactive, set_audit_context
 from .document_validation import DocumentValidationError, validate_document
+from .document_storage import DocumentStorageError, stage_document, storage_event
 
 
 ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".jpg", ".jpeg", ".png"}
@@ -175,40 +175,48 @@
     ).first()
     if previous is not None:
         raise HTTPException(status_code=409, detail="Esta versión ya fue cargada")
-    next_version = (
-        db.query(func.coalesce(func.max(models.DocumentoVersion.numero_version), 0))
-        .filter(models.DocumentoVersion.id_documento == document_id)
-        .scalar()
-        + 1
-    )
-    relative = Path(str(document_id)) / f"{next_version:04d}-{uuid.uuid4().hex}{extension}"
-    destination = (upload_root() / relative).resolve()
-    if upload_root() not in destination.parents:
-        raise HTTPException(status_code=422, detail="Ruta documental no válida")
-    destination.parent.mkdir(parents=True, exist_ok=True)
-    destination.write_bytes(content)
-    set_audit_context(db, user.id_usuario)
-    version = models.DocumentoVersion(
-        id_documento=document_id,
-        numero_version=next_version,
-        hash_sha256=digest,
-        tamano_bytes=len(content),
-        nombre_original=original,
-        ruta_almacenamiento=str(relative),
-        tipo_mime=canonical_mime,
-        id_usuario_carga=user.id_usuario,
-    )
-    db.add(version)
-    try:
-        db.commit()
-    except Exception as exc:
+    try:
+        root = upload_root()
+    except OSError as exc:
         db.rollback()
-        destination.unlink(missing_ok=True)
-        raise HTTPException(
-            status_code=409, detail="No fue posible registrar la versión"
-        ) from exc
-    db.refresh(version)
-    return version
+        raise HTTPException(status_code=507, detail="No fue posible completar el almacenamiento documental.") from exc
+    try:
+        with stage_document(root, document_id, content, digest) as staged:
+            # Parent-row serialization is pending PostgreSQL QA. Existing unique
+            # constraints remain the last defense; no process-local mutex/retry.
+            next_version = (
+                db.query(func.coalesce(func.max(models.DocumentoVersion.numero_version), 0))
+                .filter(models.DocumentoVersion.id_documento == document_id)
+                .scalar() + 1
+            )
+            relative = Path(str(document_id)) / f"{next_version:04d}-{staged.operation_id}{extension}"
+            staged.publish(relative.name)
+            try:
+                set_audit_context(db, user.id_usuario)
+                version = models.DocumentoVersion(
+                    id_documento=document_id,
+                    numero_version=next_version,
+                    hash_sha256=digest,
+                    tamano_bytes=len(content),
+                    nombre_original=original,
+                    ruta_almacenamiento=str(relative),
+                    tipo_mime=canonical_mime,
+                    id_usuario_carga=user.id_usuario,
+                )
+                db.add(version)
+                db.commit()
+            except BaseException as exc:
+                storage_event('DOCUMENT_REGISTRATION_UNCONFIRMED', staged.operation_id)
+                db.rollback()
+                if not isinstance(exc, Exception):
+                    raise
+                raise HTTPException(status_code=409,
+                    detail="No fue posible confirmar el registro de la versión; consulte el historial antes de reintentar.") from exc
+            db.refresh(version)
+            return version
+    except DocumentStorageError as exc:
+        db.rollback()
+        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc
 
 
 def safe_version_path(version: models.DocumentoVersion) -> Path:
diff --git a/tests/security/test_document_validation.py b/tests/security/test_document_validation.py
--- a/tests/security/test_document_validation.py
+++ b/tests/security/test_document_validation.py
@@ -22,6 +22,7 @@
 sys.path.insert(0, str(ROOT / 'backend'))
 sys.path.insert(0, str(ROOT / 'backend/tests'))
 from app.services import document_validation as validator
+from app.services import document_storage as storage
 from _document_samples import minimal_pdf, minimal_png, minimal_jpeg, png_chunk, office_parts, package, CT, RELS, OFFICE
 
 
@@ -227,6 +228,8 @@
         ALLOWED_EXTENSIONS={'.pdf', '.docx', '.xlsx', '.jpg', '.jpeg', '.png'}, MAX_UPLOAD_BYTES=65536,
         models=SimpleNamespace(DocumentoVersion=Version), require_document_access=MagicMock(),
         set_audit_context=MagicMock(), HTTPException=HTTPError,
+        DocumentStorageError=storage.DocumentStorageError, stage_document=storage.stage_document,
+        storage_event=MagicMock(),
         DocumentValidationError=validator.DocumentValidationError, validate_document=validator.validate_document)
     future = ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)
     exec(compile(ast.fix_missing_locations(ast.Module(body=[future, *nodes], type_ignores=[])), 'isolated_documents', 'exec'), ns)
@@ -285,7 +288,12 @@
         self.db.commit.side_effect = RuntimeError('SS06 SYNTH DRIVER DETAIL')
         with self.assertRaises(HTTPError) as caught: self.upload(minimal_pdf())
         self.assertEqual(caught.exception.status_code, 409)
-        self.assertEqual(list(Path(self.directory.name).rglob('*.pdf')), [])
+        # SS-12: commit may already have succeeded when its response is lost.
+        # Preserve the published file; only this operation's staging is cleaned.
+        retained = list(Path(self.directory.name).rglob('*.pdf'))
+        self.assertEqual(len(retained), 1)
+        self.assertEqual(retained[0].read_bytes(), minimal_pdf())
+        self.assertEqual(list(Path(self.directory.name).rglob('.pending-*')), [])
         self.db.rollback.assert_called_once()
 
     def download(self, version, denied=False):
```

**Entrega detenida para revisión técnica.** No se ejecutan pruebas PostgreSQL QA, no se implementa el lock o reconciliador propuesto, no se cambia la descarga ni se integra/despliega esta etapa.
