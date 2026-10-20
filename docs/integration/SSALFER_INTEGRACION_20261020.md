# Integración local SSALFER F01–F06 y RBAC GIS

Rama `integration/ssalfer-mq-f01-f06-20261020`, worktree
`.worktrees/ssalfer-integracion-mq-f01-f06`.
Base `d73615f7d447159ef9512d0ef500d0ae887ee5fd` de integración MQ.
Segundo padre del merge local autorizado:
`813055ca48cc0cd82e79acee58e7ab8f9022cbb8`.
Las ramas originales permanecen en sus referencias auditadas.

## Decisión vigente

Administrador, visualizador y geógrafo leen proyectos activos. Operador lee
solo los proyectos con asignación activa. Solo se crean asignaciones a operadores.
Gestión geoespacial es exclusiva de administrador y geógrafo, también mediante
identificadores directos y consultas históricas. Esta política se aplica en API;
la presentación del frontend es una comprobación adicional.

La dependencia específica `require_gis_management` protege el router completo
`geospatial_imports` y sus 22 operaciones. Los helpers existentes conservan
las validaciones de recurso, proyecto activo, pertenencia, vigencia y lectura
histórica explícita. No se cambia `READ_ROLES` en los routers de dominio/reporting.

## Inventario y consumidores reales

Los paths siguientes tienen prefijo `/api`. Todos requieren administrador o
geógrafo. `GeoespacialAPI` está definido en `js/api/geoespacial.js`; los consumidores
se verificaron en las funciones de las pantallas, no solo en el cliente API.

| Método | Endpoint | Consumidor |
| --- | --- | --- |
| GET | `/proyectos/{id_proyecto}/importaciones` | Gestión: historial/listado |
| POST | `/proyectos/{id_proyecto}/importaciones` | Gestión: pipeline de importación general/trazo |
| POST | `/proyectos/{id_proyecto}/geoespacial/ddv/importaciones` | Gestión: carga DDV |
| POST | `/proyectos/{id_proyecto}/geoespacial/nucleos/importaciones` | Gestión: carga de núcleos |
| POST | `/proyectos/{id_proyecto}/geoespacial/parcelas/importaciones` | Gestión: carga de parcelas |
| GET | `/importaciones/{id_importacion}` | Gestión y conciliación; mapa solo en previsualización |
| GET | `/importaciones/{id_importacion}/features` | Gestión/conciliación; coincidencias temporales del mapa |
| POST | `/importaciones/{id_importacion}/baja` | Gestión: baja con motivo |
| POST | `/importaciones/{id_importacion}/confirmar` | Gestión/conciliación: confirmación explícita |
| GET | `/proyectos/{id_proyecto}/geoespacial/configuracion` | Conciliación: SRID de trabajo |
| PUT | `/proyectos/{id_proyecto}/geoespacial/configuracion` | Conciliación: configuración |
| GET | `/importaciones/{id_importacion}/resumen` | Conciliación: diagnóstico/resumen |
| GET | `/importaciones/{id_importacion}/features/{id_feature}/candidatos` | Conciliación: candidatos |
| POST | `/importaciones/{id_importacion}/features/{id_feature}/decisiones` | Conciliación: decidir elemento |
| GET | `/importaciones/{id_importacion}/features/{id_feature}/decisiones` | Conciliación: historial |
| GET | `/importaciones/{id_importacion}/features/{id_feature}/geometria` | Conciliación y capa temporal de previsualización en mapa |
| POST | `/importaciones/{id_importacion}/reconciliar` | Conciliación: nuevo ciclo |
| GET | `/importaciones/{id_importacion}/conciliaciones` | Conciliación: ciclos |
| GET | `/importaciones/{id_importacion}/conciliaciones/{id_ciclo}` | Conciliación: detalle histórico |
| GET | `/proyectos/{id_proyecto}/geoespacial/revisiones` | Conciliación: revisiones |
| GET | `/geoespacial/revisiones/{id_revision}` | Conciliación: detalle de revisión |
| POST | `/geoespacial/revisiones/{id_revision}/decisiones` | Conciliación: decidir revisión |

## Cartografía publicada y dependencia del mapa

`mapa.js` obtiene las capas vigentes desde `GET /proyectos/{id}/mapa` y los
indicadores desde `GET /proyectos/{id}/mapa/indicadores`. El resumen cartográfico
de `utils/mapaConciliacion.js:detalle` se calcula sobre ese GeoJSON ya autorizado.
Ninguna de estas operaciones necesita datos de importación.
El GeoJSON publicado conserva sus propiedades `tipo`, `id` y `nombre`;
no incorpora atributos originales de staging ni diagnósticos de conciliación.

La dependencia administrativa está en los enlaces con `id_importacion`,
`id_feature` o `vista=coincidencias`, producidos desde Gestión/Conciliación.
Esos modos muestran geometrías de staging o importaciones dadas de baja, sus
atributos originales y resultados internos. Se conserva esa previsualización
para administrador/geógrafo, incluida `incluir_inactivas=true`. Operador y
visualizador reciben el mapa vigente y un aviso; no se solicitan rutas internas.
La autorización API sigue rechazando sus solicitudes directas.

La separación utiliza las rutas existentes de cartografía publicada y de
administración. No se introduce una API nueva ni se cambian DTO, campos JSON,
coordenadas, criterios de indicadores o límites de paginación.

También conservan su política previa las lecturas cartográficas/de dominio de
núcleos, parcelas, vínculos del proyecto y trazos. Las escrituras geométricas
`PATCH /nucleos/{id}/geometria`, `PATCH /parcelas/{id}/geometria` y
`POST /proyectos/{id}/trazos` ya requieren administrador/geógrafo.

| Familia / condición | Sin sesión | Admin | Geógrafo | Operador asignado | Operador sin asignación | Visualizador sin asignación |
| --- | --- | --- | --- | --- | --- | --- |
| Administración GIS, proyecto activo | 401 | Permitido | Permitido | 403 | 403 | 403 |
| Edición geométrica de núcleo/parcela y alta de trazo | 401 | Permitido | Permitido | 403 | 403 | 403 |
| Capas publicadas e indicadores, proyecto activo | 401 | 200 | 200 | 200 | 403 | 200 |
| Datos de un proyecto inactivo | 401 | 403 | 403 | 403 | 403 | 403 |
| Previsualización GIS histórica explícita | 401 | Permitido | Permitido | 403 | 403 | 403 |
| Recurso GIS inexistente, consulta puntual | 401 | 404 | 404 | 403 | 403 | 403 |

Los permisos no sustituyen las validaciones funcionales: una escritura autorizada
puede devolver 409/422. Se mantienen las convenciones existentes: un proyecto
inexistente responde 403; importación, geometría de feature, ciclo o revisión
inexistentes responden 404 a un rol GIS autorizado. La lista de candidatos de
un feature inexistente conserva su lista vacía previa. La baja de importación
responde 404 en lectura normal y permite historia solo con el parámetro explícito
y un proyecto activo. Las geometrías retiradas no reaparecen en el mapa vigente.

## Migración 030 autorizada

Las pruebas con sesión real detectaron que el trigger
`fn_gis_revision_decision_contexto` de 026 exigía asignación a un geógrafo para
guardar una decisión de revisión. La API lo autorizaba, pero PostgreSQL devolvía
un rechazo traducido a 409. La política de d73615f ya no permite asignar geógrafos.
El usuario autorizó expresamente la migración 030 durante esta integración.

`030_rbac_gis_revisiones.sql` reemplaza únicamente esa función: conserva actor
coincidente, usuario activo, rol admin/geógrafo, proyecto activo, bloqueo de la
revisión y comprobaciones de proyecto/núcleo/entidad del evento asociado. Retira
el requisito de asignación al geógrafo. No reescribe filas ni modifica geometrías,
permisos SQL, triggers de inmutabilidad o las migraciones históricas. Comprueba
la migración 029 canónica y la existencia del trigger antes de aplicar el cambio.
Se aplica y registra exclusivamente en el PostgreSQL desechable de validación.

### Revisión previa al commit local

Se comparó el cuerpo completo con la definición de 026, que sigue vigente en
029: solo cambia el predicado de alcance, además de usar `CREATE OR REPLACE`.
El objeto reemplazado es una función de trigger existente; se conservan su
identidad, sus permisos y los triggers que la invocan. No contiene `DROP`,
`TRUNCATE`, bajas, actualizaciones de registros ni transformaciones de datos.
El lock transaccional y las guardas de versión son controles de aplicación de
la migración, sin una política funcional adicional.

La ejecución ya registrada probó 029 → 030 en PostgreSQL/PostGIS desechable,
seguida de pruebas API y SQL de los cuatro roles. No certifica instalar todo
el linaje 001–029 desde cero. El runner `backend/scripts/run_migrations.sh`
descubre la 030 por su nombre y ejecuta su DDL y el registro de checksum en una
sola transacción; ante un fallo previo al commit se revierte la transacción.

Después de aplicar y confirmar 030, la reversión de base requiere restaurar
solo la definición previa de `fn_gis_revision_decision_contexto()` extraída de
026, mediante `CREATE OR REPLACE FUNCTION` dentro de una migración compensatoria
posterior, revisada y autorizada por separado. Se conserva el registro 030 del
ledger y las decisiones existentes. No se debe ejecutar de nuevo toda la 026
ni borrar filas para revertir esta función. Esa reversión vuelve a exigir
asignación al geógrafo y recupera el rechazo anterior de decisiones sin ella.
Revertir el commit Git por sí solo no revierte una base donde ya se aplicó 030.
No se implementó ni ejecutó una reversión en esta entrega.

Se ejecutó `git fetch origin` antes del cierre: la base remota continúa en
`d73615f7d447159ef9512d0ef500d0ae887ee5fd`, con 029 como última migración y
el checksum canónico requerido por 030. Las referencias remotas descargadas
no contienen otra 030/031 que colisione con esta numeración. No se detectaron
incompatibilidades con las referencias remotas actuales examinadas.

## Archivos y conservación de la integración

El merge incluye los 21 commits exclusivos F01–F06. Las modificaciones de
aplicación respecto de la rama base están en:

- `backend/app/routers/domain.py`, `reporting.py` y `schemas.py`: lecturas y contratos F01/F03/F04/F05/F06.
- `backend/app/services/access.py`: optimización F02 junto con el alcance de proyectos vigente en la base.
- `backend/app/services/dashboard_summary.py`, `map_summary.py` y `report_references.py`: servicios de agregación/referencias.
- `frontend-ssalfer/js/dashboard.js`, `seguimiento.js`, `mapa.js`, `estadoFinanciero.js`, `reportesConvenios.js`, `api/reportes.js`, `api/seguimiento.js`, `utils/dashboardExcel.js` y `utils/reporteColectivo.js`: consumidores optimizados, conservando permisos de la base.
- `backend/app/routers/geospatial_imports.py`, migración `030_rbac_gis_revisiones.sql` y la barrera de previsualización de `mapa.js`: corrección GIS autorizada.

Se añaden pruebas RBAC GIS y JavaScript del mapa. Se adaptan fixtures y
expectativas de las pruebas de proyectos, personas, ORV, documentos, GIS,
convenios, unidades agrarias, trámites RAN y concurrencia a la política de la
base. Se mantienen las denegaciones a operadores sin alcance y las restricciones
de escritura de los roles de lectura. La prueba de concurrencia entre dos
administradores utiliza asignaciones históricas de fixture: la API sigue
rechazando asignaciones nuevas a esos roles. El fixture F03 aísla otros proyectos
sintéticos dentro de su rollback externo, como ya hace F01.

Se actualizan el preparador desechable a 001–030, las seis descripciones de
rendimiento y este informe. El inventario completo de archivos queda en
`SSALFER_VALIDACION_20261020.json`. Las mediciones históricas JSON F01–F06 no se
reescriben ni se presentan como mediciones de producción de esta integración.

Las cuatro funciones de política de proyectos examinadas conservan el AST de
la base y el servicio de asignaciones conserva sus bytes. Los 62 archivos que
solo cambiaron en la base se conservan exactamente; los tres archivos compartidos
son `access.py`, `dashboard.js` y `seguimiento.js`. Los servicios GIS, modelos,
reporte general de convenios y migraciones 001–029 conservan sus bytes de
`813055c`. El backend del commit exclusivo `2183ab2` coincide con `c0875ff`, ya
incluido en la base; no necesita una integración adicional.

La comparación OpenAPI conserva las 140 rutas y los 193 esquemas previos.
F04/F05/F06 añaden cinco rutas y doce esquemas. Se conservan los contratos JSON
previos y se comprueba la equivalencia de las cargas funcionales autorizadas.
Las restricciones administrativas GIS son el cambio de autorización explícito;
el estado de esquema de la base desechable pasa a 030, sin cambiar su DTO.

## Pruebas y evidencia

Validación final terminada. Backend completo: **1,518 casos, 1,488 aprobados,
tres fallos preexistentes y 27 omisiones; cero errores de preparación y cero
regresiones nuevas detectadas**. Duración pytest: 877.76 s. La suite completa
no está totalmente en verde. Las mediciones originales de F01–F06 son
antecedentes históricos; las expectativas de permisos se adaptan a d73615f y a
la decisión GIS autorizada.

| Conjunto | Aprobadas | Fallidas | Omitidas |
| --- | ---: | ---: | ---: |
| Backend completo | 1,488 | 3 conocidas | 27 previas |
| F01 proyectos, dentro de la suite | 38 | 0 | 0 |
| F02 acceso, dentro de la suite | 173 | 0 | 0 |
| F03 territorial, dentro de la suite | 60 | 0 | 0 |
| F04 dashboard, dentro de la suite | 56 | 0 | 0 |
| F05 indicadores de mapa, dentro de la suite | 80 | 0 | 0 |
| F06 referencias de reportes y seguimiento, dentro de la suite | 61 + 38 | 0 | 0 |
| RBAC GIS nuevo, dentro de la suite | 35 | 0 | 0 |
| JavaScript, cinco archivos Node | 38 | 0 | 0 |
| Ajustes de fixtures de permisos, ejecución dirigida previa | 142 | 0 | 0 |

Los subconjuntos del backend no se suman nuevamente al total. Las 506 pruebas
F01–F06 y las 35 de RBAC GIS pasan también dentro de la ejecución completa,
con PostgreSQL/PostGIS y el catálogo nacional. La ejecución dirigida dejó fuera
dos mediciones F03 que sí se ejecutaron y aprobaron en la suite completa final.
La primera pasada había mostrado 35 expectativas/aislamientos obsoletos,
además de los tres fallos conocidos; la pasada final comprueba su resolución.

La infraestructura dedicada usa el proyecto Compose `ssalfer-integration-20261020`,
`backend/tests/convenio_report_compose.yml`, DB `software_pa_test`, cluster
`convenio-report-disposable`, tmpfs, red interna y sin puertos publicados.
El backend y los documentos se montan en lectura. Se restaura un esquema de
pruebas previamente guardado y catálogos sanitizados; el catálogo nacional RAN
procede de los archivos versionados y su manifiesto. No se consultan bases reales.
Las trazas de esta ejecución están en `/tmp/ssalfer-integration-20261020`.
El esquema restaurado tiene SHA256
`d83bc9d3ed0336f33c378570fe3d35b1dbfe03ce3ef252706aaa0a8b030864bb`.
El ledger 001–029 del fixture se construye con los checksums versionados; eso
no equivale a ejecutar el linaje histórico completo desde cero. La 030 sí se
ejecuta sobre ese destino, con sus guardas, y se registra su checksum real.
Los controles de linaje omitidos se mantienen como pendientes explícitos.

Comandos ejecutados desde el worktree (el preparador temporal rechaza una DB
existente y verifica nombre, cluster, almacenamiento y catálogos):

```bash
python3 /tmp/ssalfer-integration-20261020/run_backend.py prepare
python3 /tmp/ssalfer-integration-20261020/run_backend.py full-suite-final
node --test tests/frontend-ssalfer/dashboard-performance.cjs tests/frontend-ssalfer/map-performance.cjs tests/frontend-ssalfer/reports-performance.cjs tests/frontend-ssalfer/tracking-references-performance.cjs tests/frontend-ssalfer/map-gis-rbac.cjs
git diff --check
```

El runner usa `pytest -p no:cacheprovider -q --tb=short` con JUnit y monta
`jsonschema`, `attr`, `attrs` y `pyrsistent` locales en lectura bajo `/test-libs`.
No instala paquetes ni usa conexiones de base fuera del proyecto dedicado.
El JSON de evidencia conserva resultados por módulo, los identificadores y
motivos de omisión, los checksums de las fuentes probadas y la preparación.

Las pruebas Node usan VM y dobles DOM/API, además de generar/reabrir archivos
XLSX. No certifican navegación real. No se declarará validación de navegador sin
una ejecución de navegador real y evidencia correspondiente.

Se conserva el registro F06 de tres fallos anteriores:

- `test_facetas_respetan_naturaleza_sin_depender_de_pagina`: nombre territorial sintético frente al catálogo INEGI real.
- `test_018_backfill_specific_record_from_017_transition`: expectativa histórica `sin_clasificar` frente a `termino_periodo`.
- `test_dataset_excludes_actual_additional_ran_identities`: expectativa de 51 identidades frente a 19 del dataset de pruebas.

Las 27 omisiones previas son 23 de linaje con escritura de ledger, dos backfills
DDL GIS, una reproducción RAN y una condición de administrador único. Se verificó
la igualdad de los 27 identificadores y motivos con la ejecución F06 anterior,
sin habilitar guardas para ocultarlas. Los tres identificadores de fallo también
coinciden exactamente. La advertencia Starlette/httpx preexistente permanece.

El error Excel con `tipo_convenio=null` sigue explícitamente reproducido:
`replaceAll` sobre `null` impide generar el XLSX del dashboard en ese caso.
Su prueba pasa porque comprueba el mismo error en referencia y optimización;
eso no significa que esa exportación funcione. Las otras pruebas generan y
reabren XLSX y verifican resultados. Corregir el defecto queda fuera de esta
autorización.

## Cierre local autorizado

Se revisaron **71 archivos preparados respecto de la base**, con inventario exacto y
evidencia en [SSALFER_VALIDACION_20261020.json](SSALFER_VALIDACION_20261020.json).
Ese JSON conserva la captura de validación previa al commit, incluidos sus
campos `merge_committed=false` y `merge_head`; no describe el estado posterior
del historial Git. Antes de confirmar se verificaron `HEAD=d73615f` y
`MERGE_HEAD=813055c`, los dos padres previstos. No hay entradas sin resolver
ni archivos temporales, respaldos o cambios ajenos en el índice. La revisión
de credenciales solo encontró valores sintéticos de fixtures desechables.

Los 242 hashes de fuentes probadas coinciden con el worktree y el índice.
No cambió código después de la ejecución validada y no se repitió la suite.
El único ajuste de este cierre es documental, dentro de los mismos 71 archivos.
`git diff --cached --check` se exige antes de crear el commit. Las ramas
originales y sus worktrees permanecen sin cambios.

El usuario autorizó confirmar únicamente el merge commit local. La publicación
de la rama y de un Draft Pull Request queda pendiente de autorización, con los tres fallos, las
27 omisiones, el defecto Excel y la navegación de navegador pendiente. Los
contratos, la seguridad probada y las seis fases se conservan; estos resultados
no certifican navegación real ni equivalen a una autorización de despliegue.
El entorno donde se pruebe esta rama debe incluir 030 para que las decisiones
del geógrafo no vuelvan a ser rechazadas por el trigger anterior.

La base y la red desechables del proyecto `ssalfer-integration-20261020` se
eliminaron al cerrar la validación. Se conserva la evidencia JSON y las trazas
locales. Este cierre crea únicamente el commit local autorizado; no hace push,
PR, otro merge ni despliegue y no modifica bases reales. Se detiene después del
commit local y de comprobar el worktree limpio.

Para revisar el resultado confirmado localmente, desde la raíz del repositorio:

```bash
git -C .worktrees/ssalfer-integracion-mq-f01-f06 status
git -C .worktrees/ssalfer-integracion-mq-f01-f06 show --no-patch --format=fuller HEAD
git -C .worktrees/ssalfer-integracion-mq-f01-f06 diff HEAD^1 HEAD --stat
git -C .worktrees/ssalfer-integracion-mq-f01-f06 diff HEAD^1 HEAD -- backend/app/routers/geospatial_imports.py backend/db/migrations/030_rbac_gis_revisiones.sql frontend-ssalfer/js/mapa.js
```
