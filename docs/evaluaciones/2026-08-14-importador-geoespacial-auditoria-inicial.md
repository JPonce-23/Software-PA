# Auditoria inicial del importador geoespacial seguro

Fecha: 14 de agosto de 2026

## Estado de continuidad

- La guia de continuidad vigente documenta restauracion hasta la migracion 011,
  pero el repositorio y `db_pruebas_alfredo` tienen aplicadas las migraciones
  004 a 019.
- La siguiente migracion disponible es 020. Las migraciones aplicadas no deben
  modificarse.
- La jerarquia operativa `Proyecto -> Tramo -> Tramo_Nucleo -> Afectacion` no
  requiere cambios para endurecer la importacion de nucleos.

## Implementacion anterior

- `POST /api/nucleos/importacion-masiva` lee el archivo completo, limita a 10
  MiB, acepta solo GeoJSON y escribe directamente en `nucleo_agrario` despues
  de validar todas las features.
- `POST /api/importaciones-territoriales/{tipo}/previsualizar` genera una
  previsualizacion en memoria y el cliente reenvia todos los datos para
  confirmar; no existe staging persistente ni vinculacion inmutable con el
  archivo original.
- Ambos flujos asumen SRID 4326 mediante `ST_SetSRID` sin detectar el CRS.
- Los nombres de columnas se resuelven mediante listas de alias codificadas.
- El almacenamiento privado y por streaming de documentos puede reutilizarse
  como patron. El scheduler existente es exclusivo de alertas y no es una cola
  de trabajos generica ni ofrece reanudacion.
- La imagen backend no incluye GDAL/OGR.

## Hallazgos

| ID | Prioridad | Problema | Riesgo | Ubicacion |
|---|---|---|---|---|
| GEO-01 | Critica | `ID_MUNICIPIO` e `id_municipio` de una fuente pueden terminar en `_municipio_activo*` | Un ID externo puede vincularse a una PK interna de otra entidad | `services/nucleos.py`, `services/importaciones_territoriales.py` |
| GEO-02 | Critica | Frontend inicializa `tipo_nucleo_fallback` como `ejido` | Comunidades o tipos desconocidos se convierten silenciosamente en ejidos | `NucleosImportPanel.jsx`, `ImportacionTerritorialPanel.jsx` |
| GEO-03 | Critica | Se aplica `ST_SetSRID(..., 4326)` sin detectar CRS | Coordenadas de otro CRS quedan etiquetadas, no transformadas | Ambos servicios de importacion |
| GEO-04 | Alta | La previsualizacion no persiste archivo, hash, features ni decisiones | El payload confirmado puede no corresponder al archivo revisado | Router y servicio territorial |
| GEO-05 | Alta | La ruta masiva inserta directamente y ejecuta `flush()` por nucleo | No existe revision persistente ni reanudacion segura | `services/nucleos.py` |
| GEO-06 | Alta | Un error cancela el archivo completo | Un solo feature sin nombre bloquea miles de registros validos | Ambos servicios |
| GEO-07 | Alta | Limite de 10 MiB duplicado y codificado | Archivos reales, como Chiapas, reciben 413 | Dos routers |
| GEO-08 | Alta | Identidad basada en nombre, tipo y municipio | Puede fusionar homonimos y no conserva identidad de la fuente | Funciones `_agrupar_nucleos` |
| GEO-09 | Media | No se registran transformaciones geometricas | Reparaciones o conversiones no son auditables | Servicios actuales |
| GEO-10 | Media | No existe perfil de mapeo configurable | Cada nuevo proveedor exige cambios de codigo | Frontend y servicios |
| GEO-11 | Media | No hay procesamiento observable | No existen estados, progreso ni reporte persistente | Arquitectura actual |
| GEO-12 | Media | La ruta masiva contextual mezcla catalogacion con interseccion espacial | Una carga estatal puede fallar por features no afectadas | `services/nucleos.py` |

## Integridad e indices existentes

- `nucleo_agrario.geometria_poligono` tiene indice GiST y restriccion de
  geometria valida `MultiPolygon` SRID 4326.
- Existe unicidad activa por municipio, tipo y nombre normalizado (migracion
  018).
- `franja_derecho_via.geometria_poligono` tiene indice GiST y una sola franja
  activa por tramo.
- `municipio.clave_inegi` es unica y tambien existe unicidad por entidad y
  clave.
- No existen tablas de staging, perfiles de mapeo ni alias territoriales.

## Pruebas existentes y brechas

Las pruebas actuales cubren importacion GeoJSON, atomicidad, duplicados,
municipios por nombre y concurrencia de versiones de franja. No cubren KML,
deteccion o transformacion de CRS, staging persistente, IDs externos,
reparacion controlada, confirmacion concurrente, archivos con extension falsa,
progreso ni reportes descargables.

## Decision de arquitectura

Se implementara un flujo nuevo y aislado para nucleos agrarios:

```text
archivo privado -> OGR -> staging -> mapeo -> normalizacion PostGIS
-> resolucion territorial -> revision -> confirmacion por lotes
-> nucleo_agrario -> reporte CSV
```

Las rutas heredadas se bloquearan para nuevas importaciones de nucleos, sin
alterar los demas tipos territoriales, para impedir que evadan staging.
No se crearan relaciones `tramo_nucleo` ni afectaciones.
