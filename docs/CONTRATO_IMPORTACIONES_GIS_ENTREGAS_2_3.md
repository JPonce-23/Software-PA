# Importaciones GIS: baja e información administrativa (entregas 2 y 3)

## Baja lógica (entrega 2)

`POST /api/importaciones/{id_importacion}/baja`, roles `admin` y `geografo`
con acceso GIS al proyecto. Cuerpo obligatorio:

```json
{"motivo":"Archivo sustituido antes de confirmar"}
```

Respuesta 200: el mismo `ImportacionArchivoResponse`, con `activo=false`,
`fecha_baja`, `id_usuario_baja` y `motivo_baja`. El estado de procesamiento se
conserva: SSALFER debe usar `activo` para distinguir una importación cancelada.
El motivo normalizado por `BajaRequest` admite entre 3 y 500 caracteres.

Se permiten `error` y `previsualizado` únicamente sin confirmaciones ni
referencias protegidas. Se consultan todas las versiones geométricas de
núcleos, parcelas y DDV, las features confirmadas/con destino, candidatos y
decisiones de confirmación, entregas
sucesoras y revisiones (como origen, destino o feature). No se filtra por
vigencia o actividad al comprobar las referencias. Los trazos legados se
protegen mediante sus features y la anotación de procedencia que escribe el
importador; no existe FK directa entre trazo e importación. Se admiten
`conciliacion-v2`, `conciliacion-v3-historia` y trazos `legacy-v1`.
Los antiguos núcleos/parcelas `legacy-v1`, cuyo catálogo geométrico no conserva
FK de procedencia, y pipelines desconocidos se rechazan por seguridad.

Errores: 422 para motivo ausente/inválido; 403 por rol/proyecto; 404 para ID
inexistente o escritura sobre una importación inactiva; 409 para estados
`completo`, `procesando`, `confirmando`, `subido`, `mapeado`, `cancelado`,
confirmaciones/dependencias protegidas, procedencia no demostrable o motivo
incompatible con una baja anterior. No se habilitan estados equivalentes
adicionales porque los pipelines actuales no demuestran su cancelabilidad.

Repetir el motivo original devuelve 200 sin cambiar fecha, usuario ni motivo,
aunque quien reintente sea otro usuario autorizado. Un motivo diferente da
409. Proyecto e importación se bloquean en ese orden; decisiones,
reconciliación y confirmación releen la actividad después del bloqueo.
Una baja cierra ciclos abiertos sin modificar resultados, diagnósticos,
candidatos o decisiones. No elimina archivos/registros ni cambia geometrías.
La auditoría y el cierre son transaccionales: ante fallos se revierte todo.

## Lectura histórica explícita

`GET /api/proyectos/{id_proyecto}/importaciones?incluir_inactivas=true`
permite listar activas e inactivas. El valor por defecto es `false`.
`skip`, `limit`, orden descendente de `fecha_carga` y `X-Total-Count` se
conservan; el total aplica exactamente los filtros de la consulta.

La misma opción `incluir_inactivas=true` se aplica independientemente a:

- `GET /api/importaciones/{id_importacion}`
- `GET /api/importaciones/{id_importacion}/features`
- `GET /api/importaciones/{id_importacion}/resumen`
- `GET /api/importaciones/{id_importacion}/features/{id_feature}/candidatos`
- `GET /api/importaciones/{id_importacion}/features/{id_feature}/decisiones`
- `GET /api/importaciones/{id_importacion}/features/{id_feature}/geometria`
- `GET /api/importaciones/{id_importacion}/conciliaciones`
- `GET /api/importaciones/{id_importacion}/conciliaciones/{id_ciclo}`

Siempre se exige acceso de lectura al proyecto, incluso para IDs conocidos.
SSALFER debe deshabilitar acciones sobre `activo=false`. La opción histórica
no se admite como autorización de ninguna escritura. El resumen conserva
su significado habitual: se recalcula con el universo actual en núcleos y
parcelas; no sustituye al snapshot de un ciclo solicitado.

El SHA-256 sigue siendo único entre importaciones activas para su contexto.
Después de una baja permitida puede importarse de nuevo el mismo archivo;
se crea otra importación y se conserva íntegro el historial de la anterior.
No cambian normalización (`016` ≠ `16`), candidatos ni confirmación explícita.

## Despliegue

La entrega 2 reutiliza columnas y restricciones existentes: no necesita una
migración SQL. Requiere el esquema canónico hasta 029 y el backend actualizado.
No se reescribe ni se reaplica manualmente la migración 029. Aplicar cualquier
migración pendiente únicamente mediante el runner oficial y sus checksums,
previo respaldo y verificación por el encargado del servidor.

## Universo administrativo (entrega 3)

En importaciones conciliables de núcleos y parcelas se conservan todas las
claves anteriores del resumen. `registros_administrativos` cuenta destinos
administrativos elegibles del proyecto: vínculos activos proyecto–núcleo para
núcleos; parejas proyecto–núcleo/parcela elegibles por la vista
`vw_gis_parcela_proyecto` para parcelas. Cero significa ausencia de destinos
aplicables de ese tipo. No cuenta features ni parcelas del catálogo sin vínculo.

Se añaden a `reporte` y `GET /api/importaciones/{id}/resumen`:

- `universo_administrativo_actual`: conteos calculados para esa respuesta.
- `universo_administrativo_utilizado`: contexto del último ciclo global,
  identificado mediante `id_ciclo`. No implica que todas las features hayan
  participado en él: consultar su `id_ciclo_conciliacion` y el detalle de ese
  ciclo para explicar cada feature.

Cada ciclo nuevo guarda su contexto en `resumen.universo_administrativo`,
utilizando JSONB existente, dentro de la transacción de sus resultados.
`GET .../conciliaciones`, `GET .../conciliaciones/{id_ciclo}` y la respuesta de
reconciliación exponen además el campo opcional `universo_administrativo`.
La lectura de ciclos no consulta el universo actual para rellenar datos antiguos.

Ejemplo de `GET .../resumen` para parcelas (se omiten otras claves conservadas):

```json
{
  "registros_administrativos": 1,
  "universo_administrativo_actual": {
    "version": "1",
    "origen": "actual",
    "disponibilidad": "disponible",
    "tipo_objetivo": "parcela_gpkg",
    "id_ciclo": null,
    "fecha_evaluacion": "2026-10-13T20:00:00Z",
    "nucleos_vinculados_activos": 1,
    "parcelas_elegibles_vinculadas": 1,
    "destinos_aplicables": 1,
    "advertencias": []
  },
  "universo_administrativo_utilizado": {
    "version": "1",
    "origen": "ciclo",
    "disponibilidad": "disponible",
    "tipo_objetivo": "parcela_gpkg",
    "id_ciclo": 101,
    "fecha_evaluacion": "2026-10-13T19:00:00Z",
    "nucleos_vinculados_activos": 1,
    "parcelas_elegibles_vinculadas": 0,
    "destinos_aplicables": 0,
    "advertencias": [
      {"codigo":"SIN_PARCELAS_ELEGIBLES","mensaje":"El proyecto no tiene parcelas elegibles vinculadas administrativamente."},
      {"codigo":"SIN_DESTINOS_APLICABLES","mensaje":"No hay destinos administrativos aplicables al tipo de importación."}
    ]
  }
}
```

Campos del contexto, versión `"1"`:

| Campo | Interpretación |
|---|---|
| `origen` | `actual` o `ciclo`; este último identifica un contexto histórico. |
| `disponibilidad` | `disponible`: todos los conteos conocidos; `parcial`: solo conteos demostrables por el snapshot; `no_disponible`: no puede reconstruirse. Describe disponibilidad de información, no completitud del universo administrativo. |
| `tipo_objetivo` | Tipo de importación; puede ser nulo si no hay contexto suficiente. |
| `id_ciclo` | Ciclo correspondiente; nulo en universo actual o cuando no existe ciclo histórico. |
| `fecha_evaluacion` | Momento del cálculo actual o fecha de inicio del ciclo. Nula si no existe evidencia histórica. |
| `nucleos_vinculados_activos` | Cantidad de vínculos activos proyecto–núcleo con núcleo activo. |
| `parcelas_elegibles_vinculadas` | Parejas administrativas elegibles por la vista canónica del proyecto. |
| `destinos_aplicables` | Destinos del tipo conciliado; coincide con el conteo anterior en el resumen actual. |
| `advertencias` | Lista de código estable y mensaje; solo se emite ausencia si el conteo correspondiente está demostrado como cero. |

Advertencias estables: `SIN_NUCLEOS_VINCULADOS`, `SIN_PARCELAS_ELEGIBLES` y
`SIN_DESTINOS_APLICABLES`. No se afirma incompletitud ni se establecen umbrales.
SSALFER puede mostrar las advertencias mediante el código y utilizar el mensaje
como texto por defecto. Un proyecto con un núcleo y sin parcelas elegibles se
diferencia de uno sin núcleos mediante los dos conteos, aun si ambos tienen cero
destinos parcelarios. Las advertencias son informativas y no bloquean residuales.

Para ciclos anteriores a esta entrega, un snapshot de núcleos permite contar
núcleos/destinos, pero no parcelas; uno de parcelas permite contar
parcelas/destinos, pero no todos los núcleos (omite núcleos sin parcela elegible).
El conteo desconocido se devuelve `null`, nunca cero inferido. Los backfills 026
con `universo_historico_no_reconstruible=true`, y las importaciones anteriores
sin ciclos, devuelven `no_disponible`, los tres conteos nulos y ninguna
advertencia de ausencia. No se actualizan snapshots ni resultados antiguos.

`reporte` es el resumen persistido de la última operación que lo calculó
(staging, decisión, reconciliación o finalización); sus campos `actual` reflejan
`fecha_evaluacion` de esa operación. `GET .../resumen` recalcula contra las
relaciones actuales. Para el universo utilizado inicialmente, leer el primer
ciclo; para una feature, su ciclo específico. DDV y trazo conservan su resumen
anterior: no usan conciliación con el universo administrativo núcleo/parcela.

## Normalización parcelaria: cobertura parcial

La migración 029 ya ofrece diagnósticos de variantes comprobables de formato.
Son sugerencias para revisión humana. `016` y `16` siguen siendo distintos,
los sufijos siguen siendo significativos, y candidatos, identidad histórica,
decisiones y confirmación explícita no cambian. La equivalencia automática
queda fuera de alcance hasta aprobar una política funcional. No hay migración
para equivalencias ni inventario esperado que permita declarar incompletitud.

La entrega 3 tampoco requiere migración: utiliza el JSONB y las restricciones
de ciclo existentes. Los ciclos cerrados continúan protegidos contra cambios.
