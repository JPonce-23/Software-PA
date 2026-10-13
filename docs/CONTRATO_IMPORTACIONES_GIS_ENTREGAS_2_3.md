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
núcleos, parcelas y DDV, las features confirmadas/con destino, entregas
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
