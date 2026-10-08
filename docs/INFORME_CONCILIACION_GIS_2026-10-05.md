# Informe de conciliación GIS — 2026-10-05

> **Alcance histórico (aclaración documental, 2026-10-08):** Informe histórico de la fase previa a la renumeración canónica y a 026. Las referencias a 024 GIS y los límites de publicación del mapa describen aquel corte. El contrato vigente usa `conciliacion-v3-historia`, incluye ciclos/revisiones y B-07 publica geometrías vigentes por proyecto con fallback legacy; véanse [MIGRACIONES.md](MIGRACIONES.md), [ARQUITECTURA.md](ARQUITECTURA.md) y [API.md](API.md). Se conservan los inventarios y resultados originales.

Repositorio Software-PA; rama `feature/backend-importacion-geoespacial`. Sin commit ni push. La única base utilizada para migraciones y tests fue `software_pa_test`.

## 1. AUDITORÍA DE LOS CUATRO GPKG

Lectura directa de los cuatro originales de `fuentes_locales/gpkg`, mediante GDAL/OGR 3.10.3 y SQLite en modo sólo lectura. No se buscaron versiones alternativas ni se utilizaron KMZ para diseñar el contrato. Nombres exactos respetados.

| Archivo | Capa espacial | Features | Geometría | Dimensión | EPSG | Unidad | Validez | Tablas auxiliares | Campos de matching | Problemas |
|---|---|---:|---|---|---:|---|---|---|---|---|
| TMQ_DDV.gpkg | `TMQ_DDV` | 1 | MULTIPOLYGON | XYZ | 32614 | metro | 1 válidas, 0 inválidas | layer_styles (1 fila) + sistema GPKG/RTree | No requerido: DDV del proyecto | Tabla auxiliar layer_styles; Z; sin líneas |
| TMQ_NUCLEOS_AGRARIOS.gpkg | `TMQ_NUCLEO AGRARIO` | 64 | MULTIPOLYGON | XYZ | 32614 | metro | 64 válidas, 0 inválidas | layer_styles (1 fila) + sistema GPKG/RTree | NombreNucl, TipoNucleo, NombreMuni, NombreEnti; FRENTE contextual | No existe cve_unica; layer_styles; Z |
| TMQ_PARCELAS.gpkg | `TMQ_PARCELAS` | 997 | MULTIPOLYGON | XYZ | 32614 | metro | 997 válidas, 0 inválidas | layer_styles (1 fila) + sistema GPKG/RTree | N__CLEO_AG, TIPO_N__CL, MUNICIPIO, ESTADO, PARCELA, Num_parcela | No existe cve_unica_nucleo; 704 discrepancias; atributos excluidos; Z |
| TMQ_OBRAS TRANSVERSALES.gpkg | `oBRAS TRANSVERSALES` | 88 | POLYGON | XYZ | 32614 | metro | 88 válidas, 0 inválidas | Sistema GPKG/RTree | NOMENCLATURA, OFICIO, FRENTE (auditoría únicamente) | Fuera de alcance; Z |

Los cuatro archivos tienen una sola capa espacial. No hay geometrías vacías, nulas, GeometryCollection, líneas ni duplicados geométricos exactos por WKB. Z está presente y actualmente vale cero en todos los vértices, sin generalizar esa propiedad a futuras fuentes. DDV contiene dos componentes poligonales y no requiere soporte lineal.

Parcelas: `PARCELA` informado en 806 features; `Num_parcela` en 894; ambos en 792; ninguno en 89; sólo PARCELA en 14 y sólo Num_parcela en 102. Entre las 792 con ambos, 88 coinciden y 704 discrepan, tanto en texto como bajo la normalización estrecha aprobada. Ejemplos sin datos personales: `16 Z-1 P 1/1` / `016`, `4 Z-1 P1/1` / `004`, `100 Z-1 P2/2` / `100`. No se deduce una precedencia ni se elimina zona, polígono, letras o ceros.

## 2. ESTADO INICIAL DEL BACKEND

Existían migraciones 020–023, DDV MultiPolygon 4326 versionado, staging/importaciones con SHA y auditoría, importadores GPKG estrictos por claves oficiales y endpoints compartidos. Los importadores de núcleos/parcelas escribían geometrías globales; el preflight contaba layer_styles como capa y fallaba al leer su CRS. Las claves exigidas no existen en las entregas actuales. La conversión de Z no garantizaba XY. La deduplicación sólo por proyecto/objetivo/SHA impedía un reprocesamiento con otro pipeline o CRS.

La corrección previa `COORDINATE_PRECISION=15` ya estaba presente y se conservó. `Parcela` no tiene vínculo directo con proyecto: el universo autorizado es únicamente el vínculo administrativo existente por afectación, según decisión expresa del usuario.

## 3. DISEÑO IMPLEMENTADO

Se preserva Proyecto/ProyectoNucleo y el modelo administrativo completo. Las tablas `proyecto_nucleo_geometria` y `proyecto_parcela_geometria` añaden únicamente geometrías versionadas al destino existente, con procedencia hacia staging/importación. Los campos globales legacy siguen disponibles y no reciben nuevas escrituras de importación. `importacion_feature_candidato` expresa 0..N destinos tipados y `importacion_feature_decision` conserva cada decisión de forma append-only.

El staging no modifica dominio. Seleccionar tampoco. Confirmar un candidato autorizado guarda geometría y decisión en una transacción, con bloqueos, revalidación de pertenencia/identidad/geometría previa, aceptación de advertencias y restricciones únicas. Rechazar o ignorar no escribe geometría. La finalización admite conciliación parcial y features sin destino; exige resolver o ignorar candidatos/ambiguos pendientes y errores.

## 4. MIGRACIÓN

`backend/db/migrations/024_conciliacion_gis_proyecto.sql`, SHA-256 `c1a6684b06682ba63a9ad090c561d1cf2b9fee5b0fc1ce0da7f6c0a7952399c4`. Crea cinco tablas complementarias y la vista del universo administrativo de parcelas. Amplía archivo/feature/DDV; añade FKs, checks de validez/dimensión/SRID, GiST, índices de vigencia/versión/selección/idempotencia, triggers de ámbito/RBAC/inmutabilidad/CRS y auditoría. No modifica 020–023 ni elimina geometrías/datos existentes.

Aplicada exclusivamente a `software_pa_test` con las tres guardas y verificación previa de `current_database()`. El contrato SQL 024 se ejecutó con rollback. El esquema de la base habitual no fue modificado.

## 5. CRS

El CRS real de los cuatro archivos es EPSG:32614, WGS 84 / UTM zone 14N, metros. No se usa como CRS nacional. `proyecto_configuracion_gis.srid_trabajo` permite un CRS explícito por proyecto; sin configuración se conserva 4326. El CRS/WKT fuente y el de trabajo se fijan en cada importación. Staging guarda WKB original y XY normalizada en 4326 y en el CRS de trabajo. Cuando origen válido y trabajo coinciden se conserva la geometría XY nativa sin reproyección de ida/vuelta.

Las transformaciones y la reducción XYZ/XYM/XYZM a XY quedan registradas. No se usa Z para matching. Un cambio de configuración invalida staging previo para confirmación; una vez existen geometrías confirmadas se rechaza el cambio hasta disponer de reproyección explícita. El endpoint de geometría de staging devuelve GeoJSON en 4326 con 15 decimales; la adaptación del mapa queda para otra fase.

## 6. DDV

Acepta sólo Polygon/MultiPolygon, normaliza a MultiPolygon XY y conserva superficie, versionado, historial, activo independiente de vigente, fuente/fecha, importación y SHA. Una capa + layer_styles es válida. No acepta líneas, no genera buffers ni anchos, no interpreta intersecciones como afectaciones. Sólo se repara invalidez real de origen con warning y aceptación explícita; una invalidez creada por el pipeline es error.

## 7. NÚCLEOS

El universo son los ProyectoNucleo activos del proyecto. Una clave oficial aportada se verifica dentro de ese universo y no se inventa. Sin clave, nombre/territorio/tipo disponibles generan candidatos con normalización de Unicode, acentos, caja y espacios, sin fuzzy matching. Incluso una coincidencia exacta exige confirmación. Fuentes no vinculadas al proyecto quedan sin destino.

## 8. PARCELAS

Sólo se buscan parcelas previamente vinculadas por Afectacion → AfectacionUnidadAgraria → UnidadAgraria → Parcela en el ProyectoNucleo correspondiente. `PARCELA` y `Num_parcela` se conservan y evalúan por separado: ambos hacia el mismo destino = fuerte; uno = revisión; destinos distintos = ambiguo; ninguno = sin coincidencia. `P-585A/B/C/D` son diferentes. Se mantiene únicamente la equivalencia aprobada P.-dígitos/P-dígitos, sin reglas generales de puntuación ni eliminación de letras.

## 9. FEATURES GIS ADICIONALES

Los tests comparan conteos de Proyecto, ProyectoNucleo, NucleoAgrario, Parcela, Afectacion y expediente antes/después de staging/confirmación. Se prueban extras, claves fuera del proyecto y parcelas del mismo núcleo sin vínculo administrativo: no crean registros ni reciben destinos ajenos. La pertenencia se calcula por relaciones activas; ninguna intersección crea una relación.

## 10. DATOS PERSONALES

Se filtran atributos al guardar y al responder, también en filas históricas. No se usan ni se conservan titular, CURP, domicilio, fecha de nacimiento o certificados personales. `Name` y `NOM_SEDATU` se excluyen por semántica innecesaria/incierta; sólo se conservan campos territoriales, números originales e identificadores técnicos permitidos. La copia de carga se elimina al terminar staging; se conservan SHA, nombre, WKB/FID, CRS y atributos permitidos. Los GPKG originales permanecen intactos e ignorados por Git.

## 11. ARCHIVOS MODIFICADOS

- `backend/app/models.py`
- `backend/app/schemas.py`
- `backend/app/routers/geospatial_imports.py`
- `backend/app/services/geospatial_imports.py`
- `backend/app/services/gis_ingestion.py`
- `backend/app/services/gis_attributes.py`
- `backend/app/services/gis_reconciliation.py`
- `backend/db/migrations/024_conciliacion_gis_proyecto.sql`
- `backend/db/tests/024_conciliacion_gis_proyecto_contract.sql`
- `backend/tests/test_auth_rbac.py`
- `backend/tests/test_geospatial_imports.py`
- `backend/tests/test_nucleus_gpkg_imports.py`
- `backend/tests/test_parcel_gpkg_imports.py`
- `backend/tests/test_gis_confirmation_024.py`
- `backend/tests/test_gis_preflight_024.py`
- `docs/MIGRACIONES.md`
- `docs/DICCIONARIO_DATOS.md`
- `docs/ARQUITECTURA.md`
- `docs/INFORME_CONCILIACION_GIS_2026-10-05.md`

Los dos documentos no versionados de derechos colectivos ya existían antes de esta tarea y no se modificaron.

## 12. ENDPOINTS

Rutas bajo `/api`; se conserva el prefijo común existente.

| Método | Ruta | Cambio |
|---|---|---|
| POST | `/proyectos/{id}/geoespacial/{ddv,nucleos,parcelas}/importaciones` | Reutilizada: preflight/staging/política CRS y candidatos. |
| POST | `/proyectos/{id}/importaciones` | Reutilizada: polígonos pasan a conciliación por proyecto; trazo legacy preservado. |
| GET | `/proyectos/{id}/importaciones`, `/importaciones/{id}`, `/importaciones/{id}/features` | Reutilizadas; filtro estado_conciliacion y atributos permitidos. |
| POST | `/importaciones/{id}/confirmar` | Reutilizada: DDV versionado o finalización de conciliación. |
| GET / PUT | `/proyectos/{id}/geoespacial/configuracion` | Nueva: consultar/configurar CRS de trabajo. |
| GET | `/importaciones/{id}/resumen` | Nueva: universo y resultado de conciliación. |
| GET | `/importaciones/{id}/features/{fid}/candidatos` | Nueva: 0..N destinos propuestos. |
| GET / POST | `/importaciones/{id}/features/{fid}/decisiones` | Nueva: historial y seleccionar/confirmar/rechazar/ignorar. |
| GET | `/importaciones/{id}/features/{fid}/geometria` | Nueva: GeoJSON 4326 de staging. |

Ejemplo de confirmación, tras consultar los candidatos de una feature (seleccionar es opcional y no escribe dominio):

```json
{
  "accion": "confirmar",
  "id_candidato": 123,
  "confirmacion_explicita": true,
  "aceptar_advertencias": false
}
```

Los IDs del ejemplo deben sustituirse por los devueltos por el API. Para finalizar se utiliza el endpoint existente con `{"confirmacion_explicita": true}`; no confirma candidatos pendientes de forma implícita.

Escritura GIS sólo admin/geografo con acceso autorizado al proyecto; lectura conserva los cuatro roles existentes. No se implementó frontend ni se modificó `/mapa`.

## 13. PRUEBAS

Fixtures pequeños sintéticos, sin GPKG reales versionados. Cobertura: auxiliares/0–2 capas, CRS conocido/desconocido/32614, XY/XYZ no cero, Polygon/MultiPolygon, inválida/vacía/GeometryCollection/tipos rechazados; precisión con anillo estrecho y componentes separados mediante ST_IsValid/ST_NumGeometries/ST_NPoints; error de topología creado por pipeline; SHA/idempotencia por versión/CRS; DDV histórico/única vigente/rollback/concurrencia; candidatos sin escritura, rechazo/ignorado/parcialidad/duplicados; núcleos por clave/texto/territorio; parcelas por ambas columnas/sufijos/afectación; ámbito ajeno y pérdida de vínculo; RBAC y decisiones inmutables.

La concurrencia usa conexiones independientes para núcleos, parcelas y DDV. Se incluyó una regresión real del importador lineal y se ejecutan los tests existentes de auth/RBAC, mapa, dominio, migraciones y endpoints legacy en la suite completa.

Aceptación local de los tres archivos operativos reales, sólo lectura y validación técnica (sin confirmar ni crear registros administrativos):

| Archivo | Features válidas XY | Errores | Reparaciones | Componentes origen/normalizado | Puntos origen/normalizado |
|---|---:|---:|---:|---|---|
| TMQ_DDV.gpkg | 1 | 0 | 0 | 2/2 | 34730/34730 |
| TMQ_NUCLEOS_AGRARIOS.gpkg | 64 | 0 | 0 | 76/76 | 10171/10171 |
| TMQ_PARCELAS.gpkg | 997 | 0 | 0 | 998/998 | 7357/7357 |

Los 1062 polígonos operativos preservan validez, componentes y puntos. Obras transversales sólo se auditó.

## 14. RESULTADOS

| Ejecución | Passed | Failed | Skipped | Warnings |
|---|---:|---:|---:|---:|
| Última ejecución dirigida (preflight, DDV, legacy, parcelas, confirmación) | 60 | 0 | 0 | 1 |
| Suite completa (406 tests recogidos) | 405 | 0 | 1 | 1 |
| Contrato SQL 024 | Correcto | 0 | 0 | 0 |

La suite completa incluye 71 tests GIS: 9 DDV, 11 núcleos, 16 parcelas, 21 preflight, 11 confirmación y 3 importación/legado. Incluye también auth/RBAC, mapa, dominio y contratos de esquema existentes. La suite completa tardó 479.57 s; la última ejecución dirigida, 112.87 s.

El warning es la deprecación existente de Starlette TestClient al usar httpx. El skipped corresponde al test existente de protección del último administrador: la base aislada tiene más de un administrador activo y el propio test exige exactamente uno. No hay errores nuevos ni fallos pendientes. `git diff --check`: correcto, sin errores de whitespace.

## 15. ESTADO DE GIT

```text
 M backend/app/models.py
 M backend/app/routers/geospatial_imports.py
 M backend/app/schemas.py
 M backend/app/services/geospatial_imports.py
 M backend/app/services/gis_ingestion.py
 M backend/tests/test_auth_rbac.py
 M backend/tests/test_geospatial_imports.py
 M backend/tests/test_nucleus_gpkg_imports.py
 M backend/tests/test_parcel_gpkg_imports.py
 M docs/ARQUITECTURA.md
 M docs/DICCIONARIO_DATOS.md
 M docs/MIGRACIONES.md
?? backend/app/services/gis_attributes.py
?? backend/app/services/gis_reconciliation.py
?? backend/db/migrations/024_conciliacion_gis_proyecto.sql
?? backend/db/tests/024_conciliacion_gis_proyecto_contract.sql
?? backend/tests/test_gis_confirmation_024.py
?? backend/tests/test_gis_preflight_024.py
?? docs/DERECHOS_COLECTIVOS_PARA_FRONTEND.md
?? docs/INFORME_CONCILIACION_GIS_2026-10-05.md
?? docs/INFORME_DERECHOS_COLECTIVOS_2026-10-02.md
```

Rama: `feature/backend-importacion-geoespacial`. El índice permanece vacío (`git diff --cached` sin cambios). Los GPKG siguen ignorados; sus SHA y los de 020–023 se verificaron sin cambios. `git diff --stat` refleja 12 archivos ya versionados; se agregan 7 archivos nuevos propios de esta tarea, sin contar los 2 documentos ajenos preexistentes. El diff completo se revisó localmente.

## 16. DECISIONES PENDIENTES

No quedan decisiones humanas necesarias para este diseño antes del commit. El usuario ya delimitó las parcelas por el vínculo administrativo de afectación. La adaptación de mapa/frontend, obras transversales y un futuro cambio de CRS con geometrías existentes son fases posteriores fuera del alcance. No se hizo commit ni push.

## Anexo: detalle técnico de la auditoría

Todas las listas siguientes describen esquema/metadatos o identificadores parcelarios; no contienen valores personales. Nulos se contabilizan junto con textos vacíos. Los duplicados exactos se comprobaron por WKB; no equivalen a duplicados administrativos.

### TMQ_DDV.gpkg

SHA-256: `4bcf923952afa64e574b0df44743665dbdd1713f5d29c3d0fd852907ce181ec3`.

Tablas SQLite existentes: `TMQ_DDV`, `gpkg_contents`, `gpkg_extensions`, `gpkg_geometry_columns`, `gpkg_metadata`, `gpkg_metadata_reference`, `gpkg_ogr_contents`, `gpkg_spatial_ref_sys`, `gpkg_tile_matrix`, `gpkg_tile_matrix_set`, `layer_styles`, `rtree_TMQ_DDV_geom`, `rtree_TMQ_DDV_geom_node`, `rtree_TMQ_DDV_geom_parent`, `rtree_TMQ_DDV_geom_rowid`, `sqlite_sequence`.

Única tabla/capa espacial: `TMQ_DDV`; FID `fid`, geometría `geom`. Las restantes son tablas no espaciales de sistema/índice o estilos; las tablas de tiles existen como estructura auxiliar, sin capas raster de datos.

Geometría declarada OGR: `3D Multi Polygon`; tipos reales: `{"MULTIPOLYGON": 1}`. Dimensiones reales: `{"XYZ": 1}`; Z mínimo/máximo: `[0.0, 0.0]`.

Extensión (metros): X [356528.881392482, 484172.106106613], Y [2150802.3848133, 2281925.16793027]. CRS EPSG:32614, unidad metre.

Válidas: 1; inválidas: 0 (ningún motivo de invalidez); vacías: 0; nulas: 0; GeometryCollection: 0; duplicados WKB exactos: 0 grupos.

Componentes: 2; distribución componentes→features: `{"2": 1}`. Vértices totales (ST_NPoints/OGR): 34730.

Campos de la capa espacial:

| Campo | Tipo OGR | Tipo SQLite | Nulo/vacío |
|---|---|---|---:|
| id | String | TEXT | 0 |
| Name | String | TEXT | 0 |
| description | String | TEXT | 0 |
| timestamp | DateTime | DATETIME | 1 |
| begin | DateTime | DATETIME | 1 |
| end | DateTime | DATETIME | 1 |
| altitudeMode | String | TEXT | 1 |
| tessellate | Integer | MEDIUMINT | 0 |
| extrude | Integer | MEDIUMINT | 0 |
| visibility | Integer | MEDIUMINT | 0 |
| drawOrder | Integer | MEDIUMINT | 1 |
| icon | String | TEXT | 1 |
| id2 | String | TEXT | 0 |
| timestamp2 | String | TEXT | 1 |
| begin2 | String | TEXT | 1 |
| end2 | String | TEXT | 1 |
| altitudeMode2 | String | TEXT | 1 |
| tessellate2 | Integer | MEDIUMINT | 0 |
| extrude2 | Integer | MEDIUMINT | 0 |
| visibility2 | Integer | MEDIUMINT | 0 |
| drawOrder2 | Integer | MEDIUMINT | 1 |
| icon2 | String | TEXT | 1 |
| Frente | String | TEXT | 0 |
| Oficio | String | TEXT | 0 |
| Fecha | String | TEXT | 0 |
| Area | String | TEXT | 0 |
| ESTATUS | String | TEXT | 0 |

Tabla auxiliar OGR `layer_styles`: 1 fila(s), sin geometría. Campos: `f_table_catalog` (String), `f_table_schema` (String), `f_table_name` (String), `f_geometry_column` (String), `styleName` (String), `styleQML` (String), `styleSLD` (String), `useAsDefault` (Integer), `description` (String), `owner` (String), `ui` (String), `update_time` (DateTime).
### TMQ_NUCLEOS_AGRARIOS.gpkg

SHA-256: `a973685996780d9002dad7839612922ae62e1b5e9947e5f9f0b6cc33c30adada`.

Tablas SQLite existentes: `TMQ_NUCLEO AGRARIO`, `gpkg_contents`, `gpkg_extensions`, `gpkg_geometry_columns`, `gpkg_metadata`, `gpkg_metadata_reference`, `gpkg_ogr_contents`, `gpkg_spatial_ref_sys`, `gpkg_tile_matrix`, `gpkg_tile_matrix_set`, `layer_styles`, `rtree_TMQ_NUCLEO AGRARIO_geom`, `rtree_TMQ_NUCLEO AGRARIO_geom_node`, `rtree_TMQ_NUCLEO AGRARIO_geom_parent`, `rtree_TMQ_NUCLEO AGRARIO_geom_rowid`, `sqlite_sequence`.

Única tabla/capa espacial: `TMQ_NUCLEO AGRARIO`; FID `fid`, geometría `geom`. Las restantes son tablas no espaciales de sistema/índice o estilos; las tablas de tiles existen como estructura auxiliar, sin capas raster de datos.

Geometría declarada OGR: `3D Multi Polygon`; tipos reales: `{"MULTIPOLYGON": 64}`. Dimensiones reales: `{"XYZ": 64}`; Z mínimo/máximo: `[0.0, 0.0]`.

Extensión (metros): X [367985.534957047, 485091.247608513], Y [2175850.00999991, 2288407.54268302]. CRS EPSG:32614, unidad metre.

Válidas: 64; inválidas: 0 (ningún motivo de invalidez); vacías: 0; nulas: 0; GeometryCollection: 0; duplicados WKB exactos: 0 grupos.

Componentes: 76; distribución componentes→features: `{"1": 54, "2": 8, "3": 2}`. Vértices totales (ST_NPoints/OGR): 10171.

Campos de la capa espacial:

| Campo | Tipo OGR | Tipo SQLite | Nulo/vacío |
|---|---|---|---:|
| id | String | TEXT | 0 |
| Name | String | TEXT | 0 |
| description | String | TEXT | 0 |
| timestamp | String | TEXT | 64 |
| begin | String | TEXT | 64 |
| end | String | TEXT | 64 |
| altitudeMode | String | TEXT | 64 |
| tessellate | Integer | MEDIUMINT | 0 |
| extrude | Integer | MEDIUMINT | 0 |
| visibility | Integer | MEDIUMINT | 0 |
| drawOrder | String | TEXT | 64 |
| icon | String | TEXT | 64 |
| Name2 | String | TEXT | 64 |
| NombreNucl | String | TEXT | 0 |
| TipoNucleo | String | TEXT | 0 |
| NombreMuni | String | TEXT | 0 |
| NombreEnti | String | TEXT | 0 |
| FRENTE | String | TEXT | 56 |

Tabla auxiliar OGR `layer_styles`: 1 fila(s), sin geometría. Campos: `f_table_catalog` (String), `f_table_schema` (String), `f_table_name` (String), `f_geometry_column` (String), `styleName` (String), `styleQML` (String), `styleSLD` (String), `useAsDefault` (Integer), `description` (String), `owner` (String), `ui` (String), `update_time` (DateTime).

`cve_unica` no existe. NombreNucl/TipoNucleo/NombreMuni/NombreEnti son candidatos territoriales útiles; FRENTE se conserva como contexto, no acredita identidad ni pertenencia.
### TMQ_PARCELAS.gpkg

SHA-256: `7a2d5e42a021d9146b71b9d506e1b0651ef9c4fecb0d57a23e4fd7fcd362745a`.

Tablas SQLite existentes: `TMQ_PARCELAS`, `gpkg_contents`, `gpkg_extensions`, `gpkg_geometry_columns`, `gpkg_metadata`, `gpkg_metadata_reference`, `gpkg_ogr_contents`, `gpkg_spatial_ref_sys`, `gpkg_tile_matrix`, `gpkg_tile_matrix_set`, `layer_styles`, `rtree_TMQ_PARCELAS_geom`, `rtree_TMQ_PARCELAS_geom_node`, `rtree_TMQ_PARCELAS_geom_parent`, `rtree_TMQ_PARCELAS_geom_rowid`, `sqlite_sequence`.

Única tabla/capa espacial: `TMQ_PARCELAS`; FID `fid`, geometría `geom`. Las restantes son tablas no espaciales de sistema/índice o estilos; las tablas de tiles existen como estructura auxiliar, sin capas raster de datos.

Geometría declarada OGR: `3D Multi Polygon`; tipos reales: `{"MULTIPOLYGON": 997}`. Dimensiones reales: `{"XYZ": 997}`; Z mínimo/máximo: `[0.0, 0.0]`.

Extensión (metros): X [374901.46899998, 481885.530407815], Y [2175866.48033082, 2279250.5109999]. CRS EPSG:32614, unidad metre.

Válidas: 997; inválidas: 0 (ningún motivo de invalidez); vacías: 0; nulas: 0; GeometryCollection: 0; duplicados WKB exactos: 0 grupos.

Componentes: 998; distribución componentes→features: `{"1": 996, "2": 1}`. Vértices totales (ST_NPoints/OGR): 7357.

Campos de la capa espacial:

| Campo | Tipo OGR | Tipo SQLite | Nulo/vacío |
|---|---|---|---:|
| id | String | TEXT | 0 |
| Name | String | TEXT | 0 |
| PARCELA | String | TEXT | 191 |
| N__CLEO_AG | String | TEXT | 83 |
| TIPO_N__CL | String | TEXT | 277 |
| MUNICIPIO | String | TEXT | 84 |
| ESTADO | String | TEXT | 85 |
| SUP | String | TEXT | 94 |
| TIPO_DE_PA | String | TEXT | 318 |
| Num_parcela | String | TEXT | 103 |
| NOM_SEDATU | String | TEXT | 0 |
| GRUPO | String | TEXT | 49 |
| Frente | String | TEXT | 78 |

Tabla auxiliar OGR `layer_styles`: 1 fila(s), sin geometría. Campos: `f_table_catalog` (String), `f_table_schema` (String), `f_table_name` (String), `f_geometry_column` (String), `styleName` (String), `styleQML` (String), `styleSLD` (String), `useAsDefault` (Integer), `description` (String), `owner` (String), `ui` (String), `update_time` (DateTime).

`cve_unica_nucleo` no existe. NOM_SEDATU y Name se excluyen; no se publican sus valores. SUP tampoco se utiliza para sobrescribir superficies administrativas. Números y territorio se conservan sin reinterpretación global.
### TMQ_OBRAS TRANSVERSALES.gpkg

SHA-256: `dd6be699dfdda6952525310919a19c0461adf6c774ba8f52851543f78562498a`.

Tablas SQLite existentes: `gpkg_contents`, `gpkg_extensions`, `gpkg_geometry_columns`, `gpkg_metadata`, `gpkg_metadata_reference`, `gpkg_ogr_contents`, `gpkg_spatial_ref_sys`, `gpkg_tile_matrix`, `gpkg_tile_matrix_set`, `oBRAS TRANSVERSALES`, `rtree_oBRAS TRANSVERSALES_geom`, `rtree_oBRAS TRANSVERSALES_geom_node`, `rtree_oBRAS TRANSVERSALES_geom_parent`, `rtree_oBRAS TRANSVERSALES_geom_rowid`, `sqlite_sequence`.

Única tabla/capa espacial: `oBRAS TRANSVERSALES`; FID `fid`, geometría `geom`. Las restantes son tablas no espaciales de sistema/índice o estilos; las tablas de tiles existen como estructura auxiliar, sin capas raster de datos.

Geometría declarada OGR: `3D Polygon`; tipos reales: `{"POLYGON": 88}`. Dimensiones reales: `{"XYZ": 88}`; Z mínimo/máximo: `[0.0, 0.0]`.

Extensión (metros): X [364204.809958787, 481917.106654551], Y [2175640.10190361, 2282022.23457794]. CRS EPSG:32614, unidad metre.

Válidas: 88; inválidas: 0 (ningún motivo de invalidez); vacías: 0; nulas: 0; GeometryCollection: 0; duplicados WKB exactos: 0 grupos.

Componentes: 88; distribución componentes→features: `{"1": 88}`. Vértices totales (ST_NPoints/OGR): 2561.

Campos de la capa espacial:

| Campo | Tipo OGR | Tipo SQLite | Nulo/vacío |
|---|---|---|---:|
| id | String | TEXT | 0 |
| Name | String | TEXT | 0 |
| description | String | TEXT | 0 |
| timestamp | DateTime | DATETIME | 88 |
| begin | DateTime | DATETIME | 88 |
| end | DateTime | DATETIME | 88 |
| altitudeMode | String | TEXT | 88 |
| tessellate | Integer | MEDIUMINT | 0 |
| extrude | Integer | MEDIUMINT | 0 |
| visibility | Integer | MEDIUMINT | 0 |
| drawOrder | Integer | MEDIUMINT | 88 |
| icon | String | TEXT | 88 |
| NOMENCLATURA | String | TEXT | 0 |
| OFICIO | String | TEXT | 0 |
| FRENTE | String | TEXT | 0 |
| AREA | String | TEXT | 0 |
| FECHA_DE_OFICIO | String | TEXT | 0 |

Estructura documentada para una futura decisión cartográfica; sin modelo, tabla, endpoint, matching ni importación de negocio en esta fase.

### WKT completo del CRS común

Los cuatro WKT leídos por OGR describen el mismo CRS; se reproduce una vez para evitar redundancia.

```text
PROJCS["WGS 84 / UTM zone 14N",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",-99],PARAMETER["scale_factor",0.9996],PARAMETER["false_easting",500000],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH],AUTHORITY["EPSG","32614"]]
```
