# PR #8 — Validación nativa en PA5-QA — 2026-11-20

**Recomendación: NO MERGE.** PostgreSQL/roles/ledger/034 superaron sus contratos específicos, pero se reprodujo un desvío de la auditoría persistente mediante una tabla temporal. La herramienta final clasifica el resultado como **FAIL** y termina con código **1**. La compatibilidad del backend GDAL3.13.3 ABI39 permanece **BLOCKED** por falta de imagen e insumos de build offline autorizados.

## Alcance y procedimiento revisado

Fuente de aplicación exacta: `f715b55b964517aa4f859e9d20cbdcdee51a36ea`. Se materializaron42 archivos obtenidos del objeto Git de ese commit y se verificaron sus SHA-256 antes de ejecutar. Las herramientas QA nuevas se mantienen separadas del candidato; no se modificó contenido de las migraciones001–034.

Único destino: distribución WSL2 **PA5-QA**, Engine **`9efbaf92-7703-4fa0-9192-31b975794366`**, Docker29.10.0, linux/amd64 y almacén containerd. Se utilizó `wsl.exe --distribution PA5-QA --user root --cd /`; root fue necesario para el socket, sin cambiar sus permisos. Cada operación del launcher comprueba el Engine ID y usa explícitamente `unix:///var/run/docker.sock`, sin depender del contexto ambiente.

Antes de la primera ejecución se redactó y revisó `PROCEDIMIENTO.md`. Se reutilizaron:

- `deploy/ci/verificar-pa5-engine.sh` y `pa5-native-smoke.sh`, completos y sin cambios.
- `backend/db/init/001_bootstrap_roles.sh` y `backend/scripts/run_migrations.sh` canónicos.
- `backend/db/tests/001_runtime_privileges.sql`, mediante psql directo al socket nuevo, evitando su wrapper Compose.

No se contactó patrenes ni el Engine original de Cooper. No hubo pull/build, publicación GHCR, instalación de paquetes, cambios de daemon/conectividad, redes nuevas, push, merge o modificaciones del PR #9. Se crearon sólo contenedores propios con `--network none`, sin puertos, raíz RO, usuario postgres, límites2GiB/2CPU/256PIDs y tmpfs. Cada DB tuvo PGDATA/socket nuevos, marcador `pa5-pr8-f715b55`, owner/runtime y contraseñas aleatorias efímeras generadas dentro del contenedor. PostgreSQL no escuchó TCP y autenticó por socket con SCRAM. No se conectó a ninguna base existente.

Hubo ejecuciones adicionales únicamente por los nuevos hallazgos TEMP/auditoría. Cada una utilizó otro clúster vacío; la última omitió el smoke ya aprobado con `--database-only`. No se repitieron las800 pruebas de la auditoría anterior.

## Procedencia de los PASS previos y ejecución nueva

Los PASS de importación, smoke, bootstrap y migraciones comunicados por el usuario se conservaron como evidencia aportada. **No se reimportó la imagen.** Esta etapa verificó de nuevo el archivo, identidad y librería mediante el verificador original, y ejecutó de nuevo el smoke completo, bootstrap y migraciones en su propio clúster.

Archivo original de PA5-QA: `pa5-validated-image.tar`, SHA-256 `4099c542cf891338320396fca45fac0bc47bd1064217e70b331259981ad025b2`, coincidente al cierre.

- Índice OCI: `sha256:d413671654deef3c43367ea3fd0be56a32a36d75b9d971970e33ec56a76b7c3c`.
- Manifest amd64: `sha256:27e9ca0702414c9515cf205df5635af7ad7509385dffcf7dcf6fb048c185f9b7`.
- Config: `sha256:dfe80e1feb214799ba101b037f0b72e2499de606a63ef88497f4e13bb1ed3f19`.

Estas identidades tienen funciones distintas; el Engine containerd conserva el índice como Id/Descriptor y la referencia exacta como RepoDigest. Id, Descriptor, RootFS y RepoDigests quedaron iguales antes/después; no se alteraron hashes esperados ni la imagen.

## Dependencia Python: diagnóstico y corrección de ejecución

La imagen congelada **no contiene python3**. La invocación original sin helper se reprodujo: código127, `python3: not found`, antes de iniciar PostgreSQL. Es un prerrequisito faltante del smoke, no un fallo de GDAL/PostGIS.

Se resolvió sin reconstruirla: el launcher monta `/usr/bin/python3.12` y `/usr/lib/python3.12` de PA5-QA, RO y bajo `/qa-python`, fija PYTHONHOME/PATH y registra SHA-256 del binario y todos los archivos stdlib. Helper observado: Python3.12.3; paquetes python3.12/libpython3.12-stdlib `3.12.3-1ubuntu0.16`. No se montaron bibliotecas GDAL ni se cambió LD_LIBRARY_PATH.

Con ese helper **el script original completo terminó0**, incluyendo hashes de cinco payloads GDAL/core/bitcode, versiones exactas de paquetes, ctypes sobre GDAL ABI36, raster MEM de ida/vuelta, PostGIS/raster, geometría y LLVM/JIT con `Inlining true`. Su SHA-256 permanece `9061b54a44593fb0390ff8ce0544ef90e67a1c556e4a3553422307636764bf62`.

Versiones comprobadas: PostgreSQL SQL `15.19 (Debian15.19-1.pgdg13+2)`; PostGIS3.6.4; GDAL3.10.3 y paquetes GDAL `3.10.3+dfsg-1+pa5`. No se sustituyó ABI36 por el GDAL del host. Crear la extensión raster y el test MEM no se presentan como una campaña completa de formatos GIS.

La corrección reproducible está en `tests/qa/pa5_native_premerge/run.py` y su README. **El workflow remoto existente no monta automáticamente ese helper**: adoptar un suministro equivalente revisado/fijado sigue pendiente para su ejecución remota. Este ensayo no valida GitHub Actions ni cambia su verificador aprobado.

## Ledger y repetición real del migrador

En `software_pa_test` recién creada:

1. Bootstrap canónico: exit0.
2. Primera ejecución de las34 migraciones: exit0.
3. Comparación exacta de version/nombre/checksum contra cada SQL canónico:34/34, sin diferencias.
4. Segunda ejecución: exit0, **34 líneas verificadas**, versiones001–034 en orden, **cero reaplicaciones**.
5. Ledger idéntico antes/después del segundo pase y después de todas las pruebas de roles/034/auditoría.

Los JSON del ledger y la salida íntegra del segundo pase se conservaron. No se aceptó sólo un exit0 como prueba de idempotencia.

## Roles y DDL/DML prohibido

Contrato SQL existente: exit0. Autenticación real como runtime mediante su propia clave SCRAM, no SET ROLE desde owner. Runtime LOGIN/INHERIT, miembro de software_pa_app, sin superusuario/CREATEDB/CREATEROLE/replicación/BYPASSRLS, sin membresía del propietario ni ownership de los objetos públicos inspeccionados. El grupo es NOLOGIN y no administrador. USAGE público permitido, CREATE público denegado. El runtime puede efectuar SELECT/INSERT/UPDATE permitidos con rollback.

Los negativos adicionales exigieron SQLSTATE42501 para16 operaciones: INSERT/UPDATE/DELETE/TRUNCATE/ALTER/DROP del ledger; CREATE TABLE pública/CREATE SCHEMA; ALTER/DROP/DELETE/TRUNCATE de proyecto; CREATE ROLE, concederse owner, SET ROLE owner y desactivar triggers mediante session_replication_role. Todos produjeron la denegación esperada. Errores arbitrarios no cuentan como denegación correcta.

**Límite importante:** esto prueba restricciones sobre objetos persistentes y privilegios administrativos; no prueba ausencia de todo CREATE. El runtime conserva TEMP por los permisos PostgreSQL de la DB, y crear/usar una tabla temporal se reprodujo. La prohibición literal de crear cualquier objeto no se cumple.

## Migración034: rechazos efectivos y rollback

Sobre seed sintético válido (actor, entidad/municipio/núcleo, proyecto, afectación y convenio):

- Runtime insertó activación/retirada como dos decisiones nuevas y se observaron dos inserciones de auditoría.
- UPDATE runtime sobre una fila real: P0001 y mensaje exacto de `fn_etiqueta_fifonafe_inmutable`.
- DELETE runtime:42501 por ACL; no se presentó esa denegación como prueba del trigger DELETE.
- Como owner, con privilegio suficiente, UPDATE y DELETE fueron rechazados con P0001 y el mensaje exacto: ambos triggers fueron ejercitados.
- Se verificaron filas intactas tras los rechazos, y ausencia de etiquetas y sus bitácoras después de ROLLBACK en ambas sesiones.

Estos contratos concretos aprobaron. No se modificaron grants, deshabilitaron triggers ni cambiaron SQL para obtenerlos.

## Hallazgo de seguridad: auditoría desviada a pg_temp

**Severidad: ALTA para la integridad de auditoría. Reproducido; pendiente de corrección.** Requiere capacidad de ejecutar SQL como runtime. No se demostró una vía HTTP ni alteración del ledger ni acceso al servidor.

`public.fn_audit_log()` es SECURITY DEFINER con `search_path=public` y usa la referencia no cualificada a `bitacora`. El runtime tiene TEMP y puede crear una tabla temporal homónima. En una transacción del clúster sintético:

1. Se creó `TEMP bitacora (LIKE public.bitacora INCLUDING ALL)` como runtime.
2. Se insertó un proyecto sintético en `public.proyecto`, ejercitando su trigger real.
3. Conteos observados para ese proyecto: **public.bitacora=0; pg_temp.bitacora=1**.
4. Se revirtió todo y se verificó que el proyecto de prueba no persistió.

La fila de auditoría quedó en una relación temporal de la sesión y no en la bitácora persistente. Esto explica por qué ACL correctas sobre public.bitacora no bastan. Se reprodujo de nuevo y el launcher final terminó **1**, con `result.json.state=FAIL` y `audit_temp_shadow_reproduced=true`. Los otros20 pasos SQL/proceso terminaron0: completar el diagnóstico no significa aprobarlo.

El baseline001 es idéntico entre dev y f715b55: es un defecto preexistente, no introducido por el cambio nativo del PR. No se probó contra la base del servidor ni se extrapola su explotación allí.

**Corrección propuesta, no aplicada ni validada:** en un cambio nuevo hacia delante, sin editar001–034, poner un search_path seguro con pg_temp explícitamente al final y cualificar los objetos de auditoría. Revisar las demás funciones SECURITY DEFINER. Definir además si el runtime debe conservar TEMP; revocar sólo al runtime no basta si lo hereda de PUBLIC. La regresión posterior debe exigir una fila en public.bitacora incluso si existe una homónima temporal. PostgreSQL documenta este orden seguro para impedir el enmascaramiento de tablas ([documentación oficial PG15](https://www.postgresql.org/docs/15/sql-createfunction.html#SQL-CREATEFUNCTION-SECURITY)). No se alteró la DB para esconder el hallazgo ni se declara probado el arreglo propuesto.

## Backend GDAL3.13.3 ABI39

**BLOCKED / NOT RUN.** El inventario autorizado sólo contiene +pa5; no hay imagen backend candidata ni suministro offline demostrado de base Python fijada, fuente GDAL, paquetes apt y requirements. `build-gdal.sh` requiere aprobación explícita de build y descarga. No se hicieron descargas, builds ni cambios de conectividad para desbloquearlo.

Se preparó `BACKEND-PENDIENTE.md`: fuente exacta, suministro autorizado, `backend/native/check-gdal.py`, verificación adicional de libgdal.so.39, drivers restrictivos, clúster sintético separado y conexión por socket privado sin red nueva. Reutiliza `backend/tests/test_runtime_postgresql.py` y suites API/GIS tras revisar fixtures. El test unit/test_fifonafe_tracking.py está ligado a una DB histórica específica; no se puentearon sus guardas. La prueba SQL034 no se contabiliza como pytest/API de ese módulo.

No se mezcla GDAL3.13.3 ABI39 del backend con GDAL3.10.3 ABI36 de PostGIS. El backend efectivo del servidor no sirve como sustituto. Renderizado Compose, navegador, TLS, capacidad y SCA/SBOM instalado no se repitieron ni se declaran aprobados en esta etapa.

## Resultados y evidencia

| Área | Resultado | Código / evidencia |
|---|---|---|
| ID Engine / snapshot canónico / identidad congelada | PASS | Id autorizado;42 SHA; imagen/archivo iguales al cierre |
| Importación OCI nueva | NOT RUN | PASS previo aportado por usuario; no se repitió import |
| Verificador original de Engine/GDAL/Compose ref | PASS | exit0 |
| Smoke original sin Python | Rechazo esperado | exit127; dependencia reproducida |
| Smoke original completo con helper RO | PASS | exit0; MEM/PostGIS/raster/JIT/hashes/paquetes |
| Bootstrap y primera migración001–034 | PASS | exit0 en clúster nuevo |
| Ledger34 nombres/checksums | PASS | Comparación exacta en tres momentos |
| Segundo migrador | PASS | exit0,34 verificadas,0 reaplicadas |
| Contrato ACL existente /16 negativos adicionales | PASS | exit0;42501 esperado |
| Triggers034 runtime/owner y rollback | PASS | P0001/42501 exactos; sin filas persistidas |
| Prohibición de crear cualquier objeto | FAIL literal | TEMP permitido |
| Integridad de auditoría frente a tabla temporal | FAIL | persistent=0, temporary=1; gate final exit1 |
| Regresiones offline del launcher | PASS |4 tests,0 fallos; no Docker/WSL |
| Backend candidato / pytest de API/ABI39 | BLOCKED | Imagen/suministro no disponibles |
| CI remoto del candidato y helper | NOT RUN | Sin push; no inferir del CI de otro HEAD |

Expediente: `outputs/pr8-native-pa5-qa-20261120/`, con procedimiento previo, payloads reproducibles, logs completos, stdout/stderr, códigos y resúmenes. `evidence/` contiene el primer smoke y DB; `evidence-final/`, `evidence-audit/` y `evidence-gate/` conservan las investigaciones sucesivas sin sobrescribir las anteriores. `summary-final.json` prevalece sobre el resumen inicial antes del hallazgo. `SHA256SUMS` identifica todos los archivos.

Cierre real: Engine correcto, **cero contenedores, cero volúmenes y una imagen**, con Id/Descriptor/RootFS/RepoDigests y hash original intactos. No se eliminó ninguna imagen ni recurso ajeno. El HEAD candidato sigue siendo f715b55; quedan herramientas QA y documentación locales revisables, sin commit/push de esta etapa.

## Recomendación técnica

**NO MERGE.** El bloqueo previo de ejecutar PostgreSQL/roles/ledger/034 en un Engine independiente quedó resuelto con evidencia real. Permanecen un fallo reproducible de integridad de auditoría, su corrección/regresión pendiente y la compatibilidad del backend ABI39 no ejecutada. La existencia del defecto también en dev no autoriza declarar seguro el candidato.

Antes de reconsiderar: corregir la resolución de objetos de auditoría en un cambio nuevo revisado, repetir la regresión sin cambiar hashes históricos, resolver la política TEMP, completar el backend candidato y revisar la adopción del helper en el verificador remoto. El despliegue sobre el volumen protegido y producción siguen siendo decisiones separadas.
