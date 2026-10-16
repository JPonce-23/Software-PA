# Reporte general de convenios — contrato backend V1

Implementación local sobre `feature/backend-logica`, base
`2183ab20091f977208912f101748d5ff10c3f735`, en
`feature/reporte-general-convenios-backend`. Reutiliza el esquema 001–029;
no agrega tablas, migraciones, generación XLSX ni archivos del frontend.

## Endpoints

| GET | Parámetros | Respuesta |
| --- | --- | --- |
| `/api/proyectos/{id_proyecto}/reportes/convenios/general` | `id_entidad`, `ambito`, `naturaleza`, `pagina=1`, `tamano_pagina=100` | Cabeceras y paginación independiente por categoría |
| `/api/proyectos/{id_proyecto}/reportes/convenios/general/entidades` | `ambito`, `naturaleza` | Entidades del universo completo de ambas categorías |
| `/api/proyectos/{id_proyecto}/reportes/convenios/general/completo` | `id_entidad`, `ambito`, `naturaleza` | Todos los instrumentos del filtro, sin paginación |

IDs positivos; `ambito`: `individual` o `colectivo`. `naturaleza` filtra
`convenio.tipo_convenio`: `cop_original`, `modificatorio`,
`obras_complementarias`, `ampliacion`, `ampliacion_remanente`.
No confundir naturaleza con la clasificación operativa ORIGEN.

Se incluyen todos los instrumentos administrativamente activos, con proyecto,
vínculo proyecto-núcleo y núcleo activos. No se exige fecha de firma ni firma
acreditada. Se conservan naturaleza, modalidad, padre, estado de antecedente
y efecto de monto. `tipo_instrumento=otro` puede tener naturaleza nula.
Los originales no se eliminan por tener hijos o efectos de sustitución.

Catálogos territoriales y operativos se leen como referencias históricas:
su baja no inventa otro nombre ni reclasifica instrumentos. Las relaciones
de afectación, unidad, parcela, asamblea y eventos respetan su baja lógica.
No se buscan asambleas por coincidencia de núcleo o nombre.

## Autorización, paginación y consistencia

`RoleChecker` admite admin, operador, visualizador y geógrafo, seguido de
`require_project_access(..., load_details=False)`. Esta opción evita cargar
el grafo ORM del proyecto; su valor por defecto conserva el comportamiento
anterior. Autorización antes de filas, totales o facetas. Proyecto inexistente,
inactivo o no asignado conserva el 403 de la política actual.

Las tres rutas comparten `get_report_user`: primero ejecuta el `RoleChecker`
existente y valida el acceso al proyecto en la sesión habitual de autenticación.
Copia únicamente ID y rol a un principal inmutable y cierra esa sesión antes
de iniciar el reporte. No transporta objetos ORM con atributos expirados.
La autenticación conserva sus commits de actividad y su política habitual;
el cierre anticipado se aplica exclusivamente a estas tres rutas.

`get_report_db` depende de ese principal y crea una sesión perezosa mediante
`engine.execution_options(...)`, sin reservar conexión al construirla.
El primer SELECT adquiere una conexión `REPEATABLE READ`, `READ ONLY` y
revalida el permiso dentro del snapshot. Conteos y detalles pertenecen al mismo
snapshot. El contexto de sesión devuelve la conexión al pool ante éxito o error.
No hay conexiones de autenticación y reporte retenidas simultáneamente por
la misma solicitud. Los demás endpoints conservan `get_db` sin cambios.

Orden fijo: `id_entidad,id_municipio,id_nucleo,id_convenio`. `pagina`
(1–1,000,000) y `tamano_pagina` (1–500) se aplican independientemente a cada
categoría. `no` numera cabeceras por ámbito/filtro antes de paginar. Detalles
ordenados por IDs, destinos nulos al final. Las facetas no aceptan página ni
selección de entidad: describen todas las entidades con convenios dentro de
la naturaleza/ámbito elegidos, incluso las que no aparecen en la página.

El orden es determinista, pero páginas solicitadas en momentos diferentes
pueden reflejar cambios concurrentes. Para exportar consistentemente se usa
`/completo`, no una concatenación de peticiones paginadas.

Máximo de consulta completa: **10,000 cabeceras entre ambas categorías**.
Superarlo produce 413 antes de cargar detalles, nunca resultados parciales.
No se truncan parcelas, destinos, trámites ni eventos. El límite no corresponde
a futuras filas XLSX; el JSON completo se materializa en memoria.

Se mantiene HTTP **413** por compatibilidad con el contrato publicado. Es una
convención de este endpoint para el volumen de la respuesta solicitada, aunque
la semántica general de 413 se refiere al tamaño del contenido de una petición.
No representa una página parcial ni un error de autenticación. OpenAPI describe
la envoltura completa con `LimiteConveniosReporteResponse` y su `detail` tipado
(`LimiteConveniosReporteDetalle`). El frontend puede distinguir el límite por
el estado y `detail.codigo`, y solicitar al usuario acotar los filtros.

```json
{
  "detail": {
    "codigo": "REPORTE_EXCEDE_LIMITE",
    "limite_convenios": 10000,
    "total_convenios": 10001,
    "mensaje": "Acote los filtros; no se devolvieron datos parciales."
  }
}
```

Sesión ausente: 401. Acceso denegado: 403. Parámetros inválidos: 422.
Proyecto autorizado sin datos: 200 con listas vacías y totales cero.
Errores de infraestructura conservan los manejadores actuales de la API;
no se cambia globalmente su tratamiento HTTP.

## Datos de cabecera y colecciones

`individuales` y `colectivos`: una cabecera por `id_convenio`.
Los montos independientes `monto_total_90` y `monto_total_100` provienen de
`convenio.monto_90` y `convenio.monto_100`, en MXN. No se derivan de porcentajes,
pagos, indemnizaciones ni impactos. También se conservan en cabecera colectiva.
No se incluyen montos ni superficies declaradas dentro de parcelas o destinos.
Un total declarado no es una obligación vigente: originales y posteriores
pueden coexistir.

`parcelas` deduplica por ID, conserva `no_parcela` como texto con ceros iniciales
y referencia sus relaciones de procedencia. `destinos` agrupa por ID de destino,
incluido null. Sin unidades, permanece la cabecera con colección vacía.
`afectaciones` y `unidades` conservan IDs, rol, clasificación y superficies
de procedencia. No se unen eventos RAN con filas físicas ni se emplea
`SUM(DISTINCT importe)`.

## Superficies

Conversión exacta con Decimal: `m² = ha × 10000`. Importes y superficies JSON
son **cadenas decimales en formato fijo, sin exponentes**. Las superficies
conservan su precisión; los importes tienen exactamente dos decimales, de
acuerdo con los campos `numeric(...,2)` de origen. La validación monetaria
rechaza fracciones de centavo; no las redondea. No se convierte a float.
Los alias de serialización son exclusivos del reporte y OpenAPI 3.1 declara
patrones de cadena que coinciden con esta representación.

Ejemplos de salida real: `Decimal("0E-7")` como superficie → `"0.0000000"`;
ese mismo cero como importe → `"0.00"`; `Decimal("1E-35")` →
`"0.00000000000000000000000000000000001"`; `Decimal("-12.30")` como importe
→ `"-12.30"`. Un subtotal conocido cero también es cadena; un dato ausente
continúa siendo `null`.

Null es desconocido; cero es un dato conocido. Las procedencias siguen en ha;
todos los valores de salida indicados como superficies están en m².

| Campo | Procedencia |
| --- | --- |
| `superficie_declarada_m2` | `convenio.superficie_ha`, una vez por instrumento |
| `superficie_administrativa_afectada` | Suma de afectaciones activas vinculadas |
| `superficie_unidades` | Suma de relaciones activas afectación/unidad |
| `destinos[].superficie` | Esas relaciones agrupadas por destino |
| `afectaciones[].superficie_impacto_m2` | Impacto con signo de convenio/afectación, separado de la superficie física |
| `superficie_geometrica_m2` | Siempre null; no calculada |
| `individuales[].superficie_excel_m2` | Siempre null; correspondencia funcional pendiente |

Los resúmenes entregan `origen`, `registros`, `registros_sin_superficie`,
`subtotal_conocido_m2` y `superficie_m2`. Este último sólo tiene valor si existe
al menos una relación y todas sus superficies están presentes. Para `[0,null]`,
subtotal cero y superficie completa null; para un grupo vacío ambos son null.
No se presenta un subtotal parcial como completo.

Las superficies administrativas pueden reutilizarse entre instrumentos;
sumarlas entre convenios no produce superficie física única. No se prorratea
la superficie declarada ni se sustituye por área geométrica.

## Clasificación COP

Ámbito, naturaleza y clasificación operativa son independientes.
`tipo_cop_operativo` se obtiene de las afectaciones y catálogo, con la semántica
de la vista de 002. Un único código conocido puede acompañarse de
`clasificacion_cop_incompleta=true` si hay otras afectaciones sin clasificación.
Códigos contradictorios producen null y advertencia. Nunca se infiere ORIGEN
desde consecutivo, ámbito o naturaleza.

## Fechas RAN y asamblea

`ran_convenio` y `ran_asamblea` son independientes. Sus cuatro propiedades planas:
`fecha_ingreso_ran_convenio`, `fecha_inscripcion_ran_convenio`,
`fecha_ingreso_ran_asamblea`, `fecha_inscripcion_ran_asamblea`.

Criterio `primera_fecha_historica_por_tipo`: mínimo fechado de ingreso/reingreso
y mínimo fechado de inscripción, basado en los hitos de 006. Se reducen los
mínimos por trámite sobre los trámites activos del objetivo exacto. Es una
proyección histórica explícita, **no trámite vigente ni última situación**.
Empates: fecha, ID de trámite, ordinal e ID de evento ascendentes.

`ingreso` e `inscripcion` conservan fecha, tipo, ordinal, IDs de trámite/evento
y documento. `tramites[].eventos` conserva todos los eventos activos, también
los sin fecha. Se indica multiplicidad, cantidad de reingresos, eventos sin fecha
y si los dos hitos proceden de trámites distintos. Siempre
`tramite_vigente_determinado=false`. Programación, captura y actualización no
reemplazan hechos registrales; calificación no es inscripción. Un desistimiento
no elimina automáticamente un ingreso histórico.

La asamblea realizada procede exclusivamente de la convocatoria celebrada
activa de la asamblea autorizante activa, con su ID. No se usa programación ni
otra asamblea del núcleo. `fecha_firma_cop` es la fecha capturada, sin afirmar
acreditación documental.

## Correspondencia de las 24 columnas

| Individuales | Campo |
| --- | --- |
| NO. | `no` de cabecera |
| ESTADO / MUNICIPIO / NÚCLEO AGRARIO | `estado` / `municipio` / `nucleo_agrario` |
| NO. DE PARCELA | `parcelas[].no_parcela` |
| TIPO DE CONVENIO | `tipo_cop_operativo`, naturaleza disponible aparte |
| SUPERFICIE (M2) | `superficie_excel_m2=null`, candidatos separados |
| FIRMA DE COP | `fecha_firma_cop` |
| INGRESO / INSCRITO RAN | `fecha_ingreso_ran_convenio` / `fecha_inscripcion_ran_convenio` |
| Monto 90% / 100% | `monto_total_90` / `monto_total_100` |

| Colectivos | Campo |
| --- | --- |
| NO. | `no` de cabecera; numeración expandida se define en otra fase |
| ESTADO / MUNICIPIO / NÚCLEO AGRARIO | `estado` / `municipio` / `nucleo_agrario` |
| DESTINO / SUPERFICIE | `destinos[].nombre` / `destinos[].superficie.superficie_m2` |
| ASAMBLEA REALIZADA | `fecha_asamblea_realizada` |
| INGRESO / INSCRITO RAN de asamblea | `fecha_ingreso_ran_asamblea` / `fecha_inscripcion_ran_asamblea` |
| FIRMA DE COP | `fecha_firma_cop` |
| INGRESO / INSCRITO RAN de convenio | `fecha_ingreso_ran_convenio` / `fecha_inscripcion_ran_convenio` |

## Ejemplos

[JSON completo validado](examples/reporte_general_convenios.json): página de cada
categoría generada con fixtures **sintéticas locales**, varias parcelas, destinos,
fechas independientes y superficies incompletas. No representa datos remotos.
Esquemas completos en `docs/openapi.json` y `/openapi.json` de la API.

```text
GET /api/proyectos/123/reportes/convenios/general?pagina=1&tamano_pagina=50
GET /api/proyectos/123/reportes/convenios/general?ambito=individual&id_entidad=13
GET /api/proyectos/123/reportes/convenios/general/entidades?naturaleza=cop_original
GET /api/proyectos/123/reportes/convenios/general/completo?id_entidad=13
```

## Pruebas locales reproducibles

Desde la raíz, con imágenes ya disponibles localmente. El worker de pruebas
necesita `tests/requirements-convenio-report.txt` (JSON Schema, sólo pruebas).
En esta validación sin descargas se usaron los paquetes Python ya instalados
en Ubuntu, montando únicamente sus cuatro directorios en lectura:

```bash
docker compose -p software-pa-convenio-report-test -f backend/tests/convenio_report_compose.yml up -d --wait db
docker compose -p software-pa-convenio-report-test -f backend/tests/convenio_report_compose.yml run --rm -T --no-deps worker python tests/setup_convenio_report_db.py
report_schema_site=/usr/lib/python3/dist-packages
report_schema_mounts=(
  -v "$report_schema_site/jsonschema:/test-libs/jsonschema:ro"
  -v "$report_schema_site/attr:/test-libs/attr:ro"
  -v "$report_schema_site/attrs:/test-libs/attrs:ro"
  -v "$report_schema_site/pyrsistent:/test-libs/pyrsistent:ro"
)
docker compose -p software-pa-convenio-report-test -f backend/tests/convenio_report_compose.yml run --rm -T --no-deps "${report_schema_mounts[@]}" -e PYTHONPATH=/app:/test-libs worker pytest -q -p no:cacheprovider tests/test_convenio_general_report.py tests/test_convenio_report_connections.py tests/test_convenios_colectivos_destino.py tests/test_cierre_006_ran_ciclos.py tests/test_cierre_007_convenios_api.py tests/test_cierre_007_convenios_patch.py tests/test_ran_programacion.py tests/test_auth_rbac.py
docker compose -p software-pa-convenio-report-test -f backend/tests/convenio_report_compose.yml down -v
```

Red interna, sin puertos, imágenes sin descarga automática y datos en tmpfs.
No usa configuración ni datos de los servicios persistentes. El preparador
instala migraciones existentes sólo en el esquema vacío; rechaza otro
`cluster_name` o ledger ya instalado. No hace resets. Fixtures con rollback
externo, salvo la comprobación concurrente que escribe sólo en esta instancia
efímera. La suite verifica cardinalidades, importes, precisión, nulos, ceros,
RAN, filtros, facetas, paginación, límite, RBAC, bajas y contratos anteriores.

Hasta siete SELECT del servicio por respuesta con datos (dos para entidades),
sin crecimiento por instrumento. La autenticación conserva sus consultas fuera
de esa medición. Se comprueban READ ONLY, REPEATABLE READ y estabilidad del
snapshot ante un cambio concurrente.

Validación correctiva local del 16 de octubre de 2026: **100 passed** en
31.45 segundos (31 casos originales del reporte, 15 regresiones de contrato,
16 pruebas de conexiones y 38 regresiones existentes). Una advertencia de
deprecación Starlette/httpx. `git diff --check` sin errores y análisis sintáctico
Python sin errores.

La respuesta HTTP real, la serialización Pydantic de los valores extremos y el
ejemplo publicado validan con `Draft202012Validator` y resolución de referencias
locales a `components/schemas`, sobre OpenAPI **3.1.0** generado por la aplicación.
El ejemplo también valida contra `docs/openapi.json`, cuyos tres paths y esquemas
del reporte se comparan con los generados. No quedan errores por `0E-7`.
Los **137 paths y 177 esquemas anteriores** mantienen su contenido respecto al
commit base `2183ab20091f977208912f101748d5ff10c3f735`.

Las pruebas de conexiones ejecutan autenticación, autorización y SQL reales,
sin reemplazar dependencias FastAPI. Comprueban las tres rutas con un pool de
**una conexión y cero overflow**, rechazos 401/403 sin consultas del reporte,
liberación tras éxito y error SQL real, usuario asignado y seis peticiones
autenticadas simultáneas (las tres rutas). Observan cero conexiones reservadas
al entrar a autenticación y antes del primer SELECT del reporte. Otra prueba
HTTP comprueba el snapshot del reporte completo frente a un escritor API
concurrente; se conserva también la prueba de snapshot anterior.

No se midió carga de producción ni el volumen máximo con históricos extensos.
Los detalles completos siguen materializándose en memoria. La instancia
desechable se retiró al finalizar; no hubo conexiones a servidores remotos ni
alteraciones de bases operativas. No se verificaron datos reales de México–Querétaro.

## Decisiones pendientes

1. Superficie individual del Excel entre los candidatos expuestos.
2. Universo institucional definitivo: tipos, firma acreditada y vigencia jurídica.
3. Selección de expediente RAN vigente, si se requiere además de hitos históricos.
4. Presentación y numeración de filas con múltiples parcelas/destinos en frontend.

No se inventan reglas para resolver esos puntos. Referencia utilizada:
`fuentes_locales/excel/DOC-20261015-WA0038.xlsx`, sin modificar ni importar:
diez columnas individuales, doce colectivas y dos montos individuales adicionales.
