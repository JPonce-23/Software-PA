# SSALFER — COP completo y exportación paginada

Fecha: 2026-10-22. Referencia: `56056dd5ae0e7bc113aa2c9f953a8cc6797b62ba`.
Trabajo exclusivo en `integration/ssalfer-mq-f01-f06-20261020`, worktree `.worktrees/ssalfer-integracion-mq-f01-f06`.
El contrato se documentó antes de implementar. Este informe incorpora su diseño definitivo y las mediciones; la evidencia estructurada está en [SSALFER_COP_PAGINACION_MEDICIONES.json](SSALFER_COP_PAGINACION_MEDICIONES.json).

**Estado de alcance:** backend aditivo; frontend sin modificar. El dashboard y el Excel existentes todavía usan la primera página hasta que el responsable del frontend adopte las rutas nuevas. No se presenta este trabajo como una corrección de extremo a extremo ya instalada.

## Diagnóstico y reglas confirmadas

`dashboard_summary.project_agreements()` selecciona primero 100 IDs de `vw_proyecto_nucleo_resumen`, ordenados territorialmente. Luego obtiene los convenios alcanzables desde sus afectaciones. La deduplicación era correcta dentro de ese subconjunto, pero un convenio asociado exclusivamente al núcleo 101, 201 o 1000 quedaba fuera. Su campo `convenios` tampoco era un detalle completo del proyecto.

`domain.list_project_nuclei()` es un listado administrativo válido con `skip=0`, `limit=100`, máximo 200. Este límite de página no define el universo de indicadores. `reporting.dashboard_convenios()` consume el servicio truncado. El frontend inicia en paralelo ese GET y `NucleosAPI.listarPorProyecto()` sin recorrer páginas; usa `listaNucleos.length` para el total y registra esos mismos datos para `dashboardExcel.js`.

Se conserva expresamente la política funcional, confirmada por el responsable durante esta intervención:

- Universo: todos los vínculos `proyecto_nucleo.activo=true` del proyecto autorizado. **No se agrega `nucleo_agrario.activo`**. El núcleo del catálogo puede estar inactivo y su vínculo activo sigue participando. Un vínculo proyecto–núcleo inactivo queda excluido.
- Afectación, vínculo convenio–afectación y convenio deben estar activos. No se agregan filtros por vigencias, tipo de instrumento o categoría que no existían en COP.
- Individual/colectivo proceden de `convenio.ambito`; formalizados son los convenios de esos ámbitos con `fecha_firma IS NOT NULL`. Se cuenta cada `id_convenio` una vez. `tipo_convenio=null` sigue siendo null en la API y no cambia el cálculo.
- No se modifica `vw_dashboard_kpi`, sus fechas, importes o semántica histórica; tampoco los indicadores del mapa, que cuentan convenios firmados y tienen sus propias reglas.

`fn_validar_convenio_afectacion()` exige que convenio y afectación compartan ProyectoNucleo y ámbito. Un convenio con varias afectaciones del mismo núcleo es válido y se prueba. El vínculo a otro núcleo se rechaza por PostgreSQL; no se deshabilita el trigger para fabricar un caso prohibido. La consulta por semijoin no multiplicaría un convenio aunque varias relaciones lo alcanzasen.

## Arquitectura SQL

El nuevo resumen autoriza el proyecto con `require_project_access(..., load_details=False)` y ejecuta una única sentencia agregada. Usa tablas base con FKs obligatorias, equivalentes al conjunto de IDs de la vista, y evita sus agregaciones y relaciones de detalle:

```sql
SELECT
  (SELECT count(*) FROM proyecto_nucleo
    WHERE id_proyecto = :proyecto AND activo IS TRUE) AS total_nucleos,
  count(*) AS total_convenios,
  count(*) FILTER (WHERE c.ambito = 'individual') AS individuales,
  count(*) FILTER (WHERE c.ambito = 'colectivo') AS colectivos,
  count(*) FILTER (WHERE c.ambito IN ('individual', 'colectivo')
                    AND c.fecha_firma IS NOT NULL) AS formalizados
FROM convenio c
WHERE c.activo IS TRUE AND c.id_convenio IN (
  SELECT ca.id_convenio
  FROM convenio_afectacion ca
  JOIN afectacion a ON a.id_afectacion = ca.id_afectacion
  WHERE ca.activo IS TRUE AND a.activo IS TRUE
    AND a.id_proyecto_nucleo IN (
      SELECT id_proyecto_nucleo FROM proyecto_nucleo
      WHERE id_proyecto = :proyecto AND activo IS TRUE
    )
);
```

El `IN` es un semijoin: la fila exterior procede de la PK de convenio y no se multiplica por vínculos N:M. No se descargan IDs de todos los núcleos a Python, ni entidades ORM completas de núcleos, afectaciones o convenios. Los cinco conteos comparten el snapshot de una sentencia. La autorización agrega un SELECT y un objeto Proyecto acotado, independientemente del tamaño.

La exportación es explícita y utiliza proyecciones escalares: siete columnas de núcleo para referencias/Excel y las cinco del detalle COP heredado. Cada recurso tiene orden por su ID único ascendente, cursor y límite 200. Los nombres repetidos no afectan al cursor. El orden territorial del listado administrativo permanece intacto.

Cada página calcula contenido, total y revisión en una sola sentencia:

```sql
WITH cop_export_source AS (... proyección autorizada y única ...),
cop_export_metadata AS (
  SELECT count(*) AS total,
    md5(coalesce(string_agg(md5(row_to_json(cop_export_source)::text),
                           '' ORDER BY id_unico), '')) AS revision
  FROM cop_export_source
), cop_export_page AS (
  SELECT * FROM cop_export_source WHERE id_unico > :despues_de
  ORDER BY id_unico LIMIT :limit_mas_uno
)
SELECT metadata.*, page.*
FROM cop_export_metadata metadata LEFT JOIN cop_export_page page ON true
ORDER BY page.id_unico;
```

Se recupera como máximo `limit+1` para determinar `hay_mas`; se publican hasta `limit`. Un LEFT JOIN conserva metadatos cuando no hay filas. La huella incluye los valores exportables, incluso nombres de catálogos y fechas, y detecta ediciones que conservan el mismo número de registros. No es una credencial ni sustituye autorización.

**Coste explícito:** verificar la revisión recorre/agrega el conjunto escalar completo en PostgreSQL en cada página; no solo las 200 filas devueltas. El coste de filas examinadas de una exportación es aproximadamente O(N × páginas), con memoria SQL de la proyección y hashes O(N). Los viajes son O(páginas), no uno por registro. Este control se mantiene fuera del resumen inicial. No se presenta como trabajo constante respecto de N ni se oculta este posible cuello de botella en exportaciones mucho mayores. Las mediciones de 1000 y el ensayo de 10000 se registran por separado.

### Alternativas descartadas

- Quitar `.limit(100)` y retornar todos los convenios al abrir el dashboard: respuesta no acotada y descarga innecesaria.
- Aumentar a 200: desplaza el defecto y lo reproduce en 201.
- Recorrer núcleos/afectaciones con consultas por registro: recupera el N+1 eliminado por F04.
- Cambiar el significado del campo heredado `convenios`: rompe la equivalencia entre sus conteos y su detalle para clientes existentes.
- Reutilizar el listado administrativo para exportar: tiene una vista más costosa, muchas columnas innecesarias, offset y carece de revisión de contenido. El recurso nuevo de núcleos se justifica por su proyección mínima, cursor y control de integridad; el listado visible no cambia.
- Reutilizar el reporte general de convenios: sus reglas, proyección y finalidad no son el contrato COP operativo.
- Mantener una transacción/snapshot entre peticiones o caché persistente: requiere estado y gestión adicional de recursos. Se utiliza control optimista de contenido.

## Contrato API definitivo

Prefijo `/api`. Todas las rutas nuevas son GET; autorizan proyecto activo en cada petición. Se conservan exactamente las 145 rutas y 205 esquemas previos de `56056dd`: se añaden tres rutas y cuatro esquemas OpenAPI. `docs/openapi.json` se actualiza solo con esas adiciones; el JSON generado anterior coincide con el publicado antes de este cambio.

| Ruta relativa a `/proyectos/{id_proyecto}` | Resultado |
| --- | --- |
| `/dashboard/resumen` | Cinco totales globales; sin `convenios` ni `nucleos` |
| `/dashboard/exportacion/nucleos` | Página de `DashboardNucleoDetalle` |
| `/dashboard/exportacion/convenios` | Página de `DashboardConvenioDetalle` |
| `/dashboard/convenios` (heredada) | Sin cambios: alcance de los primeros 100 núcleos; NO garantiza detalle global completo |
| `/nucleos` (heredada) | Sin cambios: listado administrativo `skip/limit`, por defecto 100, máximo 200 |

Resumen, ejemplo sintético de 105 núcleos con un convenio por vínculo:

```json
{"total_nucleos":105,"total_convenios":105,"individuales":52,"colectivos":53,"formalizados":53}
```

Parámetros de ambas páginas:

| Parámetro | Tipo / valor inicial | Regla |
| --- | --- | --- |
| `id_proyecto` | entero positivo | Proyecto autorizado y activo |
| `despues_de` | entero >= 0, por defecto 0 | ID exclusivo; tomar `siguiente_id` de la respuesta anterior |
| `limit` | entero 1–200, por defecto 200 | No modifica la paginación administrativa |
| `revision` | 32 caracteres hexadecimales minúsculos | Opcional en la primera página; obligatorio si `despues_de > 0`; conservarlo hasta terminar |

Ejemplo de página de convenios con `limit=1` (IDs y huella ilustrativos):

```json
{
  "total": 105,
  "revision": "0123456789abcdef0123456789abcdef",
  "hay_mas": true,
  "siguiente_id": 42,
  "items": [{"id_convenio":42,"ambito":"colectivo","tipo_convenio":null,
             "consecutivo":1,"fecha_firma":"2026-01-02"}]
}
```

Página de núcleos, mismo sobre y este tipo de item:

```json
{"id_proyecto_nucleo":18,"id_nucleo":31,"nombre_nucleo":"Ejemplo",
 "id_municipio":1,"municipio":"Municipio sintético",
 "id_entidad":1,"entidad":"Entidad sintética"}
```

`total` es el número global de elementos del recurso y no depende del cursor. Última página: `hay_mas=false`, `siguiente_id=null`, aunque esté exactamente llena. Proyecto vacío: `items=[]`, `total=0`, `hay_mas=false`, `siguiente_id=null`; revisión `d41d8cd98f00b204e9800998ecf8427e`. Un cursor posterior al último ID, acompañado de revisión válida, devuelve página vacía y mantiene el total global.

Los campos de detalle no incluyen datos internos GIS, importes, geometrías o información personal. Se mantienen las categorías y fechas del convenio sin sustituciones de presentación.

| Error | Convención |
| --- | --- |
| 401 | Sesión ausente/inválida |
| 403 | Proyecto inexistente, inactivo o fuera de alcance; asignación ausente/revocada |
| 409 | `El conjunto exportable cambió; reinicie la exportación` |
| 422 | IDs/cursores/límites/revisión inválidos, o cursor no inicial sin revisión |

No se introduce 404 para el proyecto: se conserva su convención de 403. Los detalles se consultan por cursor dentro del proyecto, no mediante un acceso global por ID.

### Consistencia y concurrencia

Cada página tiene su propio snapshot PostgreSQL. Si cambia el conjunto o sus campos exportables, una petición con la revisión anterior devuelve 409 antes de entregar detalle. Esto incluye bajas y ediciones sin cambio de cantidad. Una revocación de acceso devuelve 403 aunque la revisión siga siendo la misma. Cambios ajenos a la proyección exportada que no alteren su resultado no obligan a reiniciar.

El consumidor conserva una revisión **por proyecto y recurso**, no una revisión compartida entre núcleos y convenios. Al terminar ambos conjuntos debe revalidar ambas revisiones con `despues_de=0&limit=1&revision=<original>`, comprobar los totales y obtener nuevamente el resumen. La comprobación final es necesaria para detectar cambios posteriores a la última página de un recurso mientras se recuperaba el otro. No se bloquean las escrituras ni se promete congelar el estado después de la última comprobación. Ante 409 se descartan todos los lotes y se reinicia desde cero.

## Matriz RBAC efectiva

| Recurso | Admin | Geógrafo | Visualizador | Operador asignado | Operador sin asignación/revocado |
| --- | --- | --- | --- | --- | --- |
| Resumen COP / todas las páginas de proyecto activo | 200 | 200 | 200 | 200 | 403 |
| Mapa publicado / indicadores, alcance vigente | Se conserva | Se conserva | Se conserva | Se conserva | Denegado |
| Administración GIS interna | Permitida | Permitida | 403 | 403 | 403 |
| Proyecto inactivo | 403 | 403 | 403 | 403 | 403 |

Sin sesión: 401. No se cambia `READ_ROLES`, la autorización general, las 22 operaciones GIS, ni la migración 030.

## Validación y rendimiento

Se usa PostgreSQL **15.4** / PostGIS **3.3.4** en dos proyectos Docker exclusivos: `ssalfer-cop-20261022` (captura inicial/regresiones) y `ssalfer-cop-final-20261022` (validación y mediciones finales COP), red interna sin puertos, datos en tmpfs, backend de pruebas y fuentes montadas en lectura. Se verifica nombre de base `software_pa_test` y `cluster_name=convenio-report-disposable`. No se accede a la base original del compañero ni a producción.

Se restaura el esquema de pruebas verificado hasta 029 y se aplica la 030 existente únicamente al crear esta base desechable. Ledger y checksums canónicos. No se modifica ningún SQL de migración ni se afirma una instalación nueva de todo el linaje 001–029. Catálogos sanitizados y catálogo público RAN iguales en ambos recorridos. SHA256 del esquema fuente: `d83bc9d3ed0336f33c378570fe3d35b1dbfe03ce3ef252706aaa0a8b030864bb`; 030: `aa8f3f568b3abb42751202301b980d9e5dda15db2d7070c661648445e050423d`.

### Fixtures y pruebas

`backend/tests/test_dashboard_cop_complete.py` crea proyectos de 0, 99, 100, 101, 105, 200, 201 y 1000 núcleos. Cada núcleo tiene convenio propio, con alternancia individual/colectivo, firmados/sin firma, tipo null y nombres repetidos válidos usando dos tenencias. El primer convenio tiene varias afectaciones activas para probar deduplicación. Se validan también restricciones diferidas de los fixtures; no se deshabilitan triggers.

Las pruebas incluyen conjuntos vacíos y sin convenios, convenios de la cola posterior a 100/200, bajas de PN/núcleo/afectación/vínculo/convenio, categorías/fechas, paginación con lotes de 99 y 200, ID único, páginas vacías finales, parámetros inválidos, cambios de contenido con igual cantidad, bajas y revocación entre páginas. Se comprueban los cuatro roles, operador sin asignación y revocado, sin sesión y proyecto inactivo. Hay sesiones reales con cookies para cuatro roles y operador sin asignación, además de pruebas de identidad inyectada con autorización y SQL reales.

La prueba heredada F04 que espera recorte de 100 **se conserva para la ruta heredada**. No se la presenta como una validación de totales completos. Las nuevas pruebas contrastan explícitamente el universo completo de las rutas aditivas. No se debilitan expectativas anteriores.

| Batería actual | Aprobadas | Fallidas | Omitidas |
| --- | ---: | ---: | ---: |
| COP nuevo: 78 confirmados + 3 de firma/tipo + 1 de contrato de error | **82** | 0 | 0 |
| F01–F06: seis módulos de rendimiento/regresión existentes | **468** | 0 | 0 |
| RBAC GIS existente, sesiones reales | **35** | 0 | 0 |
| Reporte general de convenios | **54** | **1 histórico** | 0 |
| Backend actual, casos únicos de estas baterías | **639** | **1 histórico** | 0 |
| JavaScript LF | **55** | 0 | 0 |
| Las mismas pruebas con CRLF simulado | **55** | 0 | 0 |

No son 110 pruebas JavaScript distintas. Son VM/DOM y generación/reapertura de XLSX en Node, no navegador. No se ejecutó una suite completa nueva del backend ni una nueva navegación real.

El fallo de reporte general reproduce exactamente `test_facetas_respetan_naturaleza_sin_depender_de_pagina`: el catálogo INEGI trae `Aguascalientes` y la expectativa histórica usa `Entidad sintética A`. Se conserva la aserción y el fallo. La batería de 558 casos tardó 1744 s, con consultas financieras heredadas largas; este tiempo global no es una comparación de latencia COP. Las 21 funciones anteriores del router y los servicios financieros no cambiaron.

Se conserva la evidencia del primer intento adicional: 77 aprobadas y un fallo al construir el fixture de 10000, antes de consultar la nueva API. Pruebas anteriores habían dejado las restricciones diferidas en IMMEDIATE. El constructor ahora usa explícitamente DEFERRED mientras crea convenio y vínculos y después fuerza ALL IMMEDIATE para comprobar su integridad. No se deshabilita ninguna restricción ni se altera backend para pasar la prueba. El proyecto grande usa además un savepoint propio para retirarlo al terminar. La ejecución confirmada de los 78 casos pasó completa. Después se añadieron y ejecutaron solo tres casos de firma/tipo, sin cambiar código backend ni repetir la batería: colectivo sin firma, individual firmado con compareciente/acreditación válidos y tipo `cop_original` no nulo. Solo cambia la fecha/tipo del convenio, no la clasificación de sus afectaciones. En la revisión final se alineó el JSON del 422 por revisión obligatoria con `HTTPValidationError` de OpenAPI; se aprobaron dos comprobaciones sin iniciar base de datos, una de ellas nueva. El cambio se limita a esa respuesta de error: se verificó por AST que todas las consultas y caminos exitosos usados en las mediciones permanecen idénticos. No se repitieron las pruebas de rendimiento por un cambio exclusivo de formato de error.

El primer intento de lanzar Node dentro del sandbox quedó bloqueado por `spawnSync git EPERM`; la repetición autorizada fuera del sandbox pasó 55/55 en ambos formatos. No se atribuye ese bloqueo a un fallo de aplicación.

### Método de medición

Antes de tocar los servicios se capturó `baseline.json` sobre los ocho tamaños. La comparación principal vuelve a ejecutar el recorrido heredado sin modificar y el nuevo sobre **los mismos registros de cada fixture y en la misma ejecución**. La captura inicial separada demuestra el defecto antes del cambio; sus tiempos no se mezclan con la tabla comparativa. Cada variante tiene calentamiento excluido y cinco muestras, mediana TestClient. No se reconstruye el antiguo N+1 para esta comparación.

El recorrido heredado inicial hace GET `/nucleos` + GET `/dashboard/convenios`. La nueva capacidad de indicadores necesita un GET `/dashboard/resumen`. Si la pantalla necesita además una página visible de núcleos, son dos GET. Se instrumentan SELECT/WITH, objetos ORM materializados, bytes reales HTTP y `tracemalloc` en muestra separada. Las métricas de ORM incluyen Proyecto de autorización, no los objetos de preparación del fixture. La autenticación se inyecta en la medición para separar su coste; las pruebas de sesiones reales son funcionales y no se mezclan con estos tiempos.

`tracemalloc` mide pico Python del proceso TestClient + aplicación + respuestas retenidas por el harness; no es RSS exclusivo del servidor ni memoria PostgreSQL. En exportación incluye la acumulación de respuestas del cliente. Las muestras de latencia se realizan sin tracing de memoria. No son tiempos TCP, navegador, renderizado, ni mediciones productivas. El recorrido controlado de API usa ambas rutas heredadas incluso en vacío; el frontend actual omite COP si su primera página está vacía. Por ello no se afirma una reducción real de HTTP del frontend para ese caso.

| Núcleos | Heredado inicial ms | Resumen completo ms | Resumen + página visible ms | JSON heredado bytes | JSON resumen bytes |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 21.34 | 16.23 | 30.02 | 67 | 88 |
| 99 | 47.37 | 20.35 | 43.71 | 121,004 | 93 |
| 100 | 55.17 | 26.32 | 46.43 | 122,418 | 95 |
| 101 | 59.93 | 26.17 | 52.72 | 122,418 | 95 |
| 105 | 58.99 | 22.61 | 50.29 | 122,418 | 95 |
| 200 | 54.66 | 24.55 | 54.59 | 122,418 | 98 |
| 201 | 63.63 | 26.97 | 52.20 | 122,418 | 98 |
| 1000 | 70.75 | 28.12 | 68.26 | 122,618 | 100 |

Consultas/peticiones: heredado **5 SELECT / 2 HTTP**; nuevo resumen **2 SELECT / 1 HTTP**; resumen + página visible **4 SELECT / 2 HTTP**, constantes en los ocho tamaños. El resumen materializa **un objeto ORM de autorización**, cero objetos de dominio funcionales y una fila agregada. Con 1000 núcleos, el pico Python es 93,529 bytes para resumen frente a 855,091 bytes del recorrido heredado.

No todas las variantes mejoran en cada escenario: en vacío, resumen + página visible mide 30.02 ms frente a 21.34 ms del recorrido heredado controlado (diferencia local de 8.68 ms; 4 SELECT frente a 5). El resumen solo mide 16.23 ms. Se muestran las cinco muestras, sin inferir significancia estadística ni ocultar este caso. La página administrativa visible sigue teniendo el coste de su vista: no se optimizó otro listado ni se presenta su latencia creciente como una propiedad del nuevo resumen. Conservarla opcional es distinto de necesitarla para calcular los totales.

### Exportación completa solicitada explícitamente

Incluye ambos recursos y dos comprobaciones finales de revisión. `filas únicas` suma núcleos y convenios, no cuenta otra vez las filas de las comprobaciones de control.

| Núcleos | HTTP | SELECT | Filas únicas | Mediana ms | JSON total bytes | Pico Python bytes |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 4 | 8 | 0 | 43.54 | 416 | 198,993 |
| 99 | 4 | 8 | 198 | 61.38 | 28,473 | 257,557 |
| 100 | 4 | 8 | 200 | 61.06 | 28,855 | 279,060 |
| 101 | 4 | 8 | 202 | 56.22 | 29,140 | 280,328 |
| 105 | 4 | 8 | 210 | 64.18 | 30,266 | 286,582 |
| 200 | 4 | 8 | 400 | 68.42 | 57,005 | 439,257 |
| 201 | 6 | 12 | 402 | 96.94 | 57,500 | 485,675 |
| 1000 | 12 | 24 | 2,000 | 276.57 | 284,058 | 820,029 |

Dos SELECT por página/control: autorización y proyección+metadatos. Cada página entrega hasta 200 filas y Python recibe hasta 201; no hay consulta por convenio/afectación. Crecen los lotes necesarios para descargar todos los datos, algo distinto de aumentar peticiones del dashboard inicial.

No se compara el tiempo de una exportación completa de 1000 contra el detalle heredado incompleto de 100 como si ambas devolvieran lo mismo. Ensayo final adicional de **10000 núcleos**, junto a los ocho proyectos estándar del fixture: resumen **38.57 ms**, **2 SELECT / 1 HTTP**, un objeto ORM de autorización y **105 bytes** de JSON. Exportación de **20000 filas únicas**: **8.52 s**, **102 HTTP / 204 SELECT**, **2,846,201 bytes** JSON acumulados y **3,910,469 bytes** de pico Python del harness. Cinco muestras del resumen y tres de exportación; no hay comparador temporal equivalente del escenario grande. El ensayo aislado anterior de un solo proyecto grande arrojó 23.75 ms / 7.63 s, pero no se compara como mejora o regresión porque no tiene los ocho proyectos de fondo ni el mismo estado físico del fixture.

El coste O(N × páginas) de las revisiones de exportación queda como límite conocido: **no se certifica escalabilidad lineal de la exportación** ni concurrencia productiva a partir de estos datos. Los 8.52 s corresponden a una descarga explícita, nunca al dashboard inicial. Para proyectos considerablemente mayores o exportaciones simultáneas debe medirse capacidad y evaluar un flujo de lotes bajo un único snapshot/transmisión o un manifiesto verificable con menos recorridos; no se introduce ahora estado persistente, una API adicional ni una migración. Este riesgo debe revisarse antes de prometer tiempos de exportación en producción.

### Alternativas de escalabilidad pendientes de evaluación

No se implementan en este commit. Se conserva la revisión de contenido por página, las comprobaciones finales y el rechazo 409; reducirlos sin un mecanismo equivalente ocultaría cambios concurrentes.

- **Transmisión por lotes desde un único snapshot:** proyectar los mismos campos y calcular una revisión coherente dentro de una sola lectura, evitando repetir el recorrido completo por cada página HTTP. Habría que evaluar duración de la transacción, cancelación, límites de memoria, reintentos y revocación de acceso. Si se exige detectar cambios posteriores al snapshot, se necesita además una comprobación final contra el estado vigente y rechazo 409 antes de aceptar el archivo.
- **Manifiesto verificable de exportación:** evaluar una revisión inicial y un manifiesto de IDs/contenido por lote, con verificación final global y descarte obligatorio ante 409. Debe detectar también ediciones con igual cantidad de registros y cambios en catálogos exportados; comparar solo conteos o el último ID no basta. Requeriría evaluar custodia del manifiesto, caducidad, autorización por página y recuperación tras interrupciones.

Ambas alternativas requieren diseño y mediciones comparables adicionales. El resultado actual de 20000 filas —8.52 s, 102 HTTP y 204 SELECT— permanece como limitación visible; no se promete una exportación lineal ni se modifica su implementación para esta publicación.

### Planes e índices

Se capturan `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` de resumen y ambas exportaciones para 100, 201 y 1000, junto con SQL compilado y `pg_indexes`. Se conservan íntegros en la evidencia. Los planes corresponden al fixture transaccional de pruebas, no a estadísticas ni distribución productivas.

En la captura de 1000, el resumen examina 1000 vínculos PN y usa semijoins/agregación de IDs alcanzables; `convenio_pkey` resuelve las filas únicas. Los scans secuenciales de afectación/vínculos recorren tablas sintéticas pequeñas (~1813 filas totales), no se confunden con consultas individuales Python. Los Nested Loop de índices dentro de una sentencia no son N+1 HTTP/SQL. Las exportaciones materializan la CTE escalar y ordenan la página; se evalúa el coste de sus agregaciones de revisión. La captura no registra derrame a disco.

| Núcleos | Resumen PostgreSQL ms | Página núcleos ms | Página convenios ms |
| ---: | ---: | ---: | ---: |
| 100 | 15.774 | 6.204 | 13.178 |
| 201 | 17.958 | 5.570 | 14.838 |
| 1000 | 22.654 | 11.982 | 20.510 |

Una ejecución EXPLAIN por sentencia y tamaño; no son medianas SQL ni se comparan directamente con TestClient.

Índices existentes relevantes: `uq_proyecto_nucleo_activo(id_proyecto,id_nucleo) WHERE activo`, `idx_afectacion_pn_tipo`, `idx_convenio_afectacion_afectacion`, `uq_convenio_afectacion_activa`, y PK de convenio/núcleo/municipio/entidad. En estas dimensiones no se justifica crear un índice nuevo. No se agregan índices, migraciones, extensiones ni dependencias.

### Referencia histórica F04

En el escenario local original de 105 núcleos: **201 → 2 HTTP, 1102 → 5 SELECT, mediana 2132 → 34 ms**. Es evidencia histórica de [F04](../performance/FASE_04_DASHBOARD.md), con su propio dataset y alcance de 100; no se presenta como la comparación temporal del fixture actual. Esta corrección mantiene acotados los viajes iniciales y evita el recorrido por registros que F04 eliminó.

## Guía para el responsable del frontend

No se ha editado `frontend-ssalfer/`. Los cambios siguientes corresponden a una intervención posterior:

1. En `dashboard.js`, consultar `/dashboard/resumen` para total de núcleos y las tres cifras COP. No derivar el total de `listaNucleos.length`, no saltar el resumen porque la página visible esté vacía y no calcular el total recorriendo afectaciones. Mantener el KPI histórico separado.
2. En `api/nucleos.js`, conservar el método del listado visible paginado. Añadir un consumidor del nuevo recurso exportable sin cambiar la semántica del método administrativo para otras pantallas.
3. Al pulsar Excel, recuperar `/dashboard/exportacion/nucleos` y `/dashboard/exportacion/convenios` en lotes de hasta 200. Comenzar cada uno con `despues_de=0`. Conservar la primera `revision` y enviarla con cada `siguiente_id`. Se puede limitar a dos recursos concurrentes; nunca una llamada por núcleo/convenio/afectación.
4. Verificar por recurso: revisión y total constantes, IDs estrictamente crecientes y únicos, avance del cursor y `items.length <= limit`. Continuar según `hay_mas`; terminar solo con `siguiente_id=null`. Verificar `IDs recibidos == total`. No suponer fin porque se llegó al antiguo 100 ni porque la última página tenga exactamente 200.
5. Revalidar ambas revisiones al finalizar con `despues_de=0&limit=1&revision=<original>` y obtener resumen nuevamente. Confirmar que sus totales de núcleos/convenios coinciden con los conjuntos descargados y con el resumen esperado. Si no coinciden, no generar un archivo parcial.
6. En `dashboardExcel.js`, generar el archivo solo después de completar y validar ambos conjuntos. Mantener `Tipo no informado` únicamente como etiqueta de presentación para null y el orden por ID de convenios. Los datos originales, categorías, fechas y cálculos no cambian.
7. Ante 409: descartar todos los lotes y ofrecer reiniciar. Ante 401: seguir la recuperación de sesión vigente. Ante 403: detener y comunicar falta de acceso. Ante red/5xx: permitir reintentar el mismo cursor/revisión; no saltar páginas ni ocultar fallos. No habilitar la descarga completa con resultados parciales.
8. Vincular cada operación a `{id_proyecto, recurso, revision}` y a un `AbortController`/generación local. Al cambiar proyecto o cerrar sesión, abortar peticiones y descartar respuestas tardías de la generación anterior. No crear un caché global reutilizable entre usuarios.
9. Conservar los cuatro roles de lectura de proyecto y las barreras de sesión/página. La disponibilidad del resumen no concede acceso a Gestión geoespacial interna.
10. Revalidar en navegador aislado: 99/100/101/200/201/1000 núcleos, cambio de proyecto durante exportación, sesión caducada, revocación, escrituras concurrentes, XLSX generado y reabierto con todas las filas y valores. Hasta integrar y ejecutar esta fase no se certifica el Excel completo ni la navegación nueva.

## Archivos modificados

| Archivo | Cambio |
| --- | --- |
| `backend/app/services/dashboard_summary.py` | Resumen completo y proyecciones/páginas; función heredada idéntica |
| `backend/app/routers/reporting.py` | Tres GET aditivos y autorización por proyecto en cada llamada |
| `backend/app/schemas.py` | DTO de resumen, núcleo y páginas; detalle de convenio reutilizado |
| `backend/tests/test_dashboard_cop_complete.py` | 82 casos, fixtures sintéticos y mediciones |
| `docs/openapi.json` | Solo tres rutas/cuatro esquemas nuevos |
| `docs/integration/SSALFER_COP_PAGINACION_COMPLETA.md` | Diagnóstico, contrato y guía para frontend |
| `docs/integration/SSALFER_COP_PAGINACION_MEDICIONES.json` | Muestras, planes, hashes, resultados y límites |

## Protección de F01–F06 y pendientes históricos

Solo se extienden `dashboard_summary.py`, `reporting.py` y esquemas; el contrato heredado permanece. F01 listado/materialización, F02 autorización acotada, F03 catálogos/listados, F05 geometrías/indicadores y F06 reportes/seguimiento/finanzas se contrastan mediante sus regresiones existentes. El cuerpo heredado `project_agreements()` permanece idéntico. Se mantienen todas las fuentes frontend, las mejoras de sesiones de `75598ba`, los guards GIS/dashboard y la migración 030.

Las **1488 aprobadas, tres fallos y 27 omisiones** de la suite completa anterior son evidencia histórica, no una nueva ejecución completa. Se conservan los tres fallos conocidos: faceta INEGI (`Aguascalientes` frente a entidad sintética), backfill 018 (`termino_periodo` frente a `sin_clasificar`) y dataset RAN (19 frente a 51 identidades). Las 27 omisiones históricas: 23 controles con escritura de ledger, dos backfills GIS, una reproducción RAN y una condición de administrador único. No se cambian expectativas para ocultarlos.

El defecto Excel `tipo_convenio=null` ya fue corregido antes de esta intervención y sigue cubierto por las pruebas JavaScript; no se atribuye su corrección al backend COP nuevo. Permanecen pendientes la integración frontend de estas capacidades, validación colaborativa con copia aislada del compañero, escrituras/decisiones GIS sin asignación y verificación de 030 en su copia. La confirmación del criterio PN activo se registra aquí; excluir el núcleo del catálogo inactivo requeriría una modificación funcional independiente autorizada.

Para repetir las pruebas, preparar primero una instancia **nueva y desechable** con el Compose de `backend/tests/convenio_report_compose.yml`, esquema canónico hasta 030 y catálogos del fixture; verificar el guard de nombre de base/cluster. La preparación utilizada se registra en el JSON (restauración del esquema verificado y bootstrap, no migración de una base existente). En ese entorno, con `COP_EVIDENCE_DIR` apuntando a una carpeta de evidencia montada fuera del checkout:

```bash
python -m pytest -p no:cacheprovider -q tests/test_dashboard_cop_complete.py
```

El módulo final contiene 82 casos; se ejecutaron 78 confirmados, tres nuevos focalizados y uno nuevo de contrato de error (junto con una repetición de la comprobación OpenAPI). Las pruebas no deben ejecutarse contra el Compose/base habituales: `conftest.py` exige `APP_ENV=test`, `DB_NAME=software_pa_test` y `TEST_ALLOW_DATABASE=software_pa_test`. El fixture agrega otro control de `cluster_name`. Los datos de preparación son sintéticos y las métricas excluyen sus INSERT/validaciones de integridad. El JSON incluye las muestras, planes, resultados, hashes y los nombres de los dos proyectos Docker; ambos se retiran al cerrar.

## Estado registrado al finalizar la validación, antes de la autorización de publicación

No se crean commits ni se publica esta intervención durante la validación. PR #2 continúa Draft; no hay push, merge de PR, despliegue ni modificaciones en producción. El estado final y los hashes de fuentes se registran al cerrar la evidencia. Para revertir este trabajo local antes de publicarlo debe revisarse su diff y retirarse solo estos archivos/cambios autorizados; no se requiere revertir datos ni migraciones porque no se introduce ninguno.

Estado de cierre: los dos contenedores PostgreSQL y sus redes exclusivas fueron retirados; sus datos estaban en tmpfs. HEAD local/remoto permanece en `56056dd`, destino remoto en `75598ba`, sin commits nuevos ni operación Git pendiente. Hay siete archivos de esta intervención sin confirmar; los worktrees originales de backend y optimizaciones permanecen limpios. PR #2 abierto y Draft, verificado en lectura.


## Revisión previa a la publicación autorizada

La autorización posterior permite confirmar estos siete archivos y publicarlos mediante push normal exclusivamente en la rama de integración. Las referencias previas se verifican en `56056dd` (integración local/remota) y `75598ba` (destino); PR #2 abierto y Draft. El estado anterior y los campos Git del JSON son una captura de la validación, no el estado posterior al push. El SHA publicado se obtiene de Git y del PR, sin incluir un SHA autorreferente en este informe.

El código backend y las pruebas conservan los hashes de la ejecución registrada: 82 COP y 557 regresiones aprobadas, más el fallo histórico INEGI; 55 JavaScript con LF y las mismas 55 con CRLF. Se reordena únicamente el documento OpenAPI para conservar el orden de claves anterior y limitar el diff a las tres rutas/cuatro esquemas aditivos; su contenido JSON es idéntico al contrato probado. No se repite la suite por este ajuste documental. No se declara validado el nuevo flujo frontend ni el Excel completo en navegador.
