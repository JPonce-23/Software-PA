# Auditoría de historia GIS y conciliación tardía — 2026-10-05

> **Alcance histórico (aclaración documental, 2026-10-08):** Informe histórico de la auditoría que precedió a la estabilización del linaje y a 026. La detención y las funcionalidades pendientes descritas abajo corresponden a esa fase; no describen el backend actual. El linaje canónico ya incluye 026 (ciclos y revisiones) y termina en 028; el pipeline actual es `conciliacion-v3-historia`. Véanse [MIGRACIONES.md](MIGRACIONES.md) y [API.md](API.md). Se conserva la evidencia del bloqueo y el diseño original.

## Resultado y límite de esta entrega

La fase de implementación de ciclos y revisiones queda detenida por la colisión
real de migraciones detectada en la auditoría Git solicitada. No se creó ninguna
migración ni endpoint nuevo. Se auditó el código local 024, se diseñó la extensión
pendiente y se añadieron regresiones que pueden ejecutarse con el esquema actual.
El criterio final de éxito de reconciliación tardía + revisiones GIS **todavía no
está implementado**. Las pruebas verdes del comportamiento existente no acreditan
esas funcionalidades pendientes.

No se hizo commit, push, merge, rebase, reset, checkout ni stash. Tampoco se
modificaron migraciones aplicadas, archivos GPKG, frontend, `/mapa` ni la rama
remota. La única base conectada para consultas y pruebas fue `software_pa_test`.

## 1. Rama y divergencia comprobada después de fetch

| Referencia | Commit |
|---|---|
| Rama activa | `feature/backend-importacion-geoespacial` |
| HEAD local | `a829f1c` — WIP: conservar avances de importación geoespacial |
| `origin/feature/backend-logica` | `49f12f7` — completar ciclo seguro de asignaciones por proyecto |
| Ancestro común | `cf07d7ea519794ee558229de88681c05e9e0fa01` |
| Divergencia | 5 commits exclusivamente locales; 2 exclusivamente remotos |

Los dos commits remotos posteriores al ancestro son `750ec71` (excluir heartbeat
de bitácora) y `49f12f7` (asignaciones, acceso de personas y concurrencia).
El índice estaba vacío antes de trabajar y sigue sin cambios staged.

La comparación remota no contiene cambios en `models.py`, `SeguimientoEvento`,
`TramiteRanEvento`, los catálogos de historia, las vistas de seguimiento ni las
reglas de afectaciones y convenios. Sí cambia `services/access.py`,
`services/domain.py`, los routers de dominio/usuarios, los tests de auditoría,
RBAC, asignaciones y personas, `conftest.py`, `docs/API.md`, `docs/MIGRACIONES.md`,
OpenAPI y documentación QA. Las referencias de personas tienen nuevas
comprobaciones de acceso y bloqueos; esto debe conservarse al integrar, también
en los flujos administrativos que sirvan de contexto a futuras revisiones GIS.

## 2. Inventario de migraciones y conflicto estructural

Las migraciones versionadas **001–019 son idénticas byte a byte** entre ambas
ramas y el workspace.

| Versión | Rama GIS / workspace | Rama remota backend-logica |
|---|---|---|
| 020 | `020_derecho_via_proyecto.sql` | `020_auditoria_heartbeat_sesion.sql` |
| 021 | `021_importacion_ddv_gpkg.sql` | Ausente |
| 022 | `022_importacion_nucleos_gpkg.sql` | Ausente |
| 023 | `023_importacion_parcelas_gpkg.sql` | Ausente |
| 024 | `024_conciliacion_gis_proyecto.sql`, local sin commit | Ausente |

Checksums incompatibles de 020:

- GIS: `3662cc9ce0ed2e63095b7a873616356aa965e94b1b34e9f651ffd5396452dc09`.
- Remota: `cfa4dadb2e8b5bb9b8cddddf617c34132380ad49a660de9037de43850263f4c8`.

024 local: `c1a6684b06682ba63a9ad090c561d1cf2b9fee5b0fc1ce0da7f6c0a7952399c4`.
`SELECT current_database()` devolvió `software_pa_test`; su ledger registra
001–024, con la 020 GIS y los checksums correspondientes al workspace.

El runner identifica una migración sólo por `version` y exige su checksum exacto.
Una integración que deje ambos archivos 020 en el directorio ejecutable falla,
aunque Git pueda combinar los nombres distintos sin conflicto textual. Ambas 020
tienen además una guarda que rechaza una versión 020 ya registrada. La remota
reemplaza `fn_audit_log`; no puede aplicarse directamente sobre esta base como si
fuera una migración adicional.

**025 no se reserva ni se declara disponible para esta fase.** La colisión previa
debe resolverse antes de asignar números a heartbeat, ciclos y revisiones.

Hallazgo adicional del workspace: existe `001_init_schema.sql` físico, ignorado
y ajeno al inventario Git canónico. El glob del runner también lo incluiría. No
se ejecutó el runner ni se borró ese archivo. Una futura ejecución debe usar un
directorio con el inventario canónico revisado, sin ese duplicado 001.

### Estrategia de integración pendiente

1. Inventariar, fuera de esta ejecución, qué entornos tienen la 020 de cada rama.
   Aquí sólo se verificó `software_pa_test`; no se consultó `db_pruebas_alfredo`.
2. Acordar una cadena canónica y una ruta de compatibilidad para los dos historiales.
   No renumerar ni reescribir 020–024 aplicadas y no corregir checksums a mano.
3. Para la cadena GIS existente, portar el cambio funcional de heartbeat mediante
   una migración **nueva forward-only**, con número acordado y precondiciones
   verificadas. Conservar el archivo 020 remoto como evidencia histórica fuera
   del conjunto ejecutable de esa cadena; no modificar la rama remota.
4. Si otros entornos ya ejecutaron 020-heartbeat, requieren una ruta de adopción
   explícita y verificada. No pueden ejecutar la cadena GIS actual por un simple
   merge ni por renombrar sus archivos. Esa ruta se debe diseñar antes de aceptar
   una única numeración global; esta entrega no altera su ledger.
5. Integrar después los cambios remotos de acceso/asignaciones con revisión de
   bloqueos y sus regresiones. El código de acceso y de historia administrativa
   debe quedar coherente antes de conectar revisiones con eventos.
6. Sólo entonces asignar la siguiente migración de ciclos/revisiones y ejecutar
   sus contratos, backfill compatible y pruebas de concurrencia.

Es posible avanzar sin esa integración con auditoría, documentación y regresiones
de 024. No es correcto añadir ahora ciclos o revisiones sin el esquema requerido.

## 3. SeguimientoEvento e historia no lineal

El modelo usa `CatalogoOperativo`, no un enum ni una máquina de estados lineal.
Los catálogos activos de la base contienen `inicio`, `suspension`, `reapertura`,
`cierre` y `cambio_alcance`, entre otros. El flujo administrativo normal es
`POST /api/proyecto-nucleo/{id}/seguimiento` →
`domain.create_seguimiento_evento` → una fila nueva.

Las migraciones 004/006 protegen tipo, motivo, objetivo, ámbito y ProyectoNucleo
frente a reescritura. Exigen fecha para las transiciones, motivo para suspensión,
detalle para reapertura y motivo/detalle para cierre y cambio de alcance. No hay
una restricción que prohíba `cierre → reapertura` ni sucesivas suspensiones.

`vw_seguimiento_estado_actual` usa la última fila activa entre **inicio,
suspension, reapertura, cierre**, ordenada por `fecha_evento DESC` y luego por
`id_seguimiento_evento DESC`, por vínculo/objetivo. `cambio_alcance`, reuniones y
otros hechos permanecen en la historia, pero no sustituyen esa transición de
estado. Por ello un cambio de alcance después de una suspensión no reabre por sí
solo el seguimiento. No existe necesidad de otro estado físico duplicado.

La documentación llama append-only a esta historia. El contrato real permite
correcciones de metadatos y baja lógica auditada mediante PATCH/DELETE; prohíbe
reescribir la identidad funcional de una transición y borrar físicamente eventos.
No se convirtió esta historia en una tabla completamente inmutable ni se cambiaron
esas reglas existentes.

## 4. RAN, ciclos COP y convenios

`TramiteRan` conserva el objetivo registral y `referencia_expediente`;
`TramiteRanEvento` conserva múltiples filas con ordinal por el mismo trámite.
Están disponibles `ingreso`, `prevencion`, `subsanacion`, `calificacion`,
`inscripcion` y `reingreso`. El API añade eventos al trámite existente; no crea
otro trámite cuando se registra un reingreso.

La regresión existente `test_cierre_006_ran_ciclos.py` cubre dos prevenciones,
subsanaciones, dos reingresos, calificación e inscripción, tanto para acta como
convenio. Comprueba identidad, orden y reporting: un ingreso realizado total,
sin nuevos ingresos computados en los meses de reingreso. Se conserva y ejecuta;
no se duplicó esa cobertura ni se modificó el modelo RAN.

Los cinco códigos COP activos se comprobaron en la base: `ORIGEN`, `ADICIONAL`,
`2A_ADICIONAL`, `COMPLEMENTARIAS`, **`TRANSVERSALES`**. Este último es operativo
y permanece intacto; no implica una capa GIS de obras transversales.

El modelo funcional y los contratos 007/016/017 conservan instrumentos repetibles,
convenio original, modificatorio, superficie adicional y obras complementarias,
linaje de convenio e impactos explícitos. Las ampliaciones deben registrarse por
el flujo administrativo correspondiente. Ningún importador GIS ejecuta esa lógica.

## 5. Auditoría de 024

| Componente | Comportamiento actual | Pendiente para esta fase |
|---|---|---|
| `proyecto_configuracion_gis` | CRS explícito; 4326 por defecto; bloquea cambio tras confirmaciones | Política métrica de comparación y tolerancia validada |
| `importacion_archivo` | SHA/pipeline/CRS/propósito/proyecto; staging nuevo para SHA diferente | Alcance declarado de entrega y referencia a entrega anterior |
| `importacion_feature` | Geometría original, XY 4326 y de trabajo; trazabilidad CRS/dimensión; confirmada inmutable | Resultado por intento sin perder staging |
| `importacion_feature_candidato` | Destinos tipados del universo administrativo; una selección/destino; confirmado inmutable | Identidad del ciclo e historia de candidatos por intento |
| `importacion_feature_decision` | Append-only por trigger y ACL; usuario/fecha/motivo/candidato | Referencia del nuevo intento sin reescribir decisiones antiguas |
| `proyecto_nucleo_geometria` | Versiones por ProyectoNucleo; una vigente; origen feature/importación | Revisión de diferencias y protección completa de procedencia histórica |
| `proyecto_parcela_geometria` | Versiones por ProyectoNucleo + Parcela; una vigente | Misma extensión técnica de revisiones |
| `vw_gis_parcela_proyecto` | Sólo vínculo administrativo activo por afectación/unidad/parcela | Se reutiliza, sin pertenencia calculada por intersección |

Las restricciones existentes cubren FKs tipadas, pertenencia al proyecto, SRID,
validez/no vacío/XY, GiST, versiones positivas y unicidad de vigencia. Las
confirmaciones bloquean proyecto/importación y revalidan y bloquean el destino;
núcleos y parcelas rechazan una geometría previa cambiada desde staging. Las
decisiones y la inserción geométrica están en la misma transacción.

**No existe ciclo de conciliación.** `build_candidates` escribe candidatos una
sola vez durante staging y la unicidad destino/feature no incorpora un intento.
Volver a invocarlo no es una reconciliación histórica segura: consulta todos los
candidatos de la feature y puede colisionar con los anteriores. Las decisiones
actuales cambian el estado del candidato como proyección mutable, y la
finalización bloquea decisiones posteriores porque exige `previsualizado`.

**No existen revisiones GIS persistentes.** Para reemplazo geométrico se usa
`ST_Equals` y se exige aceptar `GEOMETRIA_EXISTENTE_DISTINTA`; el hash WKB previo
es un token de concurrencia, no una política de relevancia espacial. No se
calculan diferencias DDV ni se detectan nuevas/desaparecidas como revisiones.

El servicio conserva versiones sin sobrescribir sus geometrías. Sin embargo,
las guardas SQL no congelan completamente `version`, `fuente`, `fecha_fuente`
y toda la procedencia histórica de las tablas geométricas. La siguiente migración
debe completar esa inmutabilidad permitiendo sólo vigencia/baja/auditoría según
la operación explícita autorizada. No se presenta esa protección pendiente como
ya implementada.

## 6. Diseño pendiente de reconciliación tardía

Se necesita una entidad de ciclo y un resultado por feature/ciclo que también
registre el resultado sin candidatos. El staging original permanece en
`importacion_archivo`/`importacion_feature`; el ciclo 1 representa la primera
conciliación y los siguientes intentos se agregan sin borrar filas.

El ciclo debe tener importación, número único dentro de ella, fecha de inicio/fin,
usuario, versión de algoritmo/reglas, motivo, estado, selección de features,
universo administrativo utilizado y resumen. El universo debe conservar IDs y
atributos de identidad efectivamente leídos, con un snapshot consistente y un
digest determinista. Un simple conteo no permite auditar qué destinos se usaron.

La operación explícita selecciona sólo sin destino/sin coincidencia; ambiguas
cuando se solicite. Rechazadas requieren una política explícita, motivo y permiso
GIS; ignoradas/confirmadas no son elegibles por defecto. Un nuevo intento puede
trabajar sobre una importación finalizada sin fingir que volvió a ser un staging
nuevo. Las confirmaciones sólo aceptan candidatos del intento vigente y
revalidan el universo actual; un candidato antiguo no se reactiva implícitamente.

La futura migración debe ajustar las unicidades de candidatos al intento y
separar resultados históricos de la proyección de selección vigente. No puede
backfillear decisiones o candidatos confirmados mediante UPDATE: sus triggers
lo rechazan y se perdería la garantía histórica. Debe usar asociaciones aditivas
o referencias nuevas nulas para historia legacy, documentando qué contexto
original no se puede reconstruir. Nunca etiquetar como universo histórico el
universo administrativo de hoy.

Los bloqueos de proyecto/importación/feature y una unicidad de número de ciclo
deben serializar reconciliaciones simultáneas. La confirmación valida ciclo,
destino y versión previa y escribe sólo geometría/decisión/revisión GIS; nunca
crea el destino administrativo tardío.

## 7. Versionado de núcleos, parcelas y DDV

Se reutilizan las tablas de 024. La confirmación explícita mantiene la geometría
anterior `activo=true, es_vigente=false` e inserta `max(version)+1` como vigente.
La restricción parcial permite sólo una vigente por ProyectoNucleo o por
ProyectoNucleo + Parcela. Las parcelas requieren la cadena administrativa activa
de la vista 024, no sólo pertenecer al núcleo. La procedencia se conserva por
feature → importación, con SHA, fuente/fecha, CRS, usuario y transformaciones.

DDV hace lo mismo por proyecto y conserva su importación, SHA y geometría de
trabajo. Cambiar la vigencia cartográfica no constituye baja lógica. Confirmar
DDV no cambia la vigencia de las geometrías de núcleos/parcelas.

La extensión añadirá la revisión correspondiente en la misma transacción de
confirmación. Una identidad previamente confirmada sólo ayudará al matching
de una entrega nueva; staging y confirmación siguen siendo explícitos.

## 8. Diseño pendiente de revisión de cambios GIS

Una revisión técnica independiente de `SeguimientoEvento` debe conservar
proyecto/destino o feature sin destino, importación anterior/nueva, referencias
tipadas de versiones geométricas y DDV, tipo de cambio, algoritmo/política,
métricas, fecha y actor. Debe tener unicidad de comparación para impedir duplicados
al reintentar el procesamiento.

Tipos: `geometria_modificada`, `aparece_en_nueva_version`,
`desaparece_en_nueva_version`, `cambio_relacion_ddv`; `sin_cambio` puede conservarse
como resultado diagnóstico sin generar trabajo pendiente artificial.
Relaciones DDV: sí→no, no→sí y ambas con variación relevante de geometría.
Una geometría administrativa sin cartografía produce comparación no evaluable,
nunca una afirmación automática de no intersección.

Las resoluciones se agregan a una historia append-only con usuario, fecha,
decisión, motivo y evento administrativo opcional. El estado actual se deriva
de esa historia: `pendiente`, `revisado`, `no_aplica`, `aplicado`. Aplicado acredita
la resolución humana y, cuando corresponda, un evento ya creado por el flujo de
dominio; no ejecuta ni replica la creación de ese evento.

La FK a un evento preexistente debe validar proyecto/ProyectoNucleo/objetivo y
actividad, con comprobación en servicio y base. El permiso de resolver o vincular
es GIS existente (`admin`, `geografo` con alcance); crear el evento conserva su
propio permiso administrativo. `operador`/`visualizador` no reciben privilegios
GIS nuevos. La lectura mantiene los roles existentes y el ámbito de proyecto.

### Comparación DDV y tolerancias

- Comparar versiones anterior/nueva en un CRS común y conservar cuáles se usaron.
  Empezar por igualdad topológica; no usar igualdad WKB para relevancia espacial.
- Calcular `ST_SymDifference`/`ST_Difference`, área y componentes únicamente como
  métricas técnicas. Para `area_diferencia_m2` exigir CRS proyectado con unidades
  métricas o una transformación métrica explícita y auditada; EPSG:4326 no
  proporciona metros cuadrados mediante `ST_Area(geometry)`.
- La política de tolerancia debe ser versionada y calibrada contra precisión y
  transformaciones de la fuente. Esta fase detenida no introduce un epsilon
  inventado. Sin política calibrada no afirmar automáticamente una modificación
  relevante basándose sólo en una diferencia numérica pequeña.
- La implementación pendiente debe probar igualdad por reordenamiento de
  vértices/componentes, errores de transformación, casos debajo/en/encima del
  umbral, huecos/componentes significativos y contacto de bordes. Conservar las
  métricas brutas y la política aplicada sin alterar superficies administrativas.
- Al confirmar DDV, comparar relaciones anterior/nueva con geometrías vigentes
  del proyecto y generar revisiones. No modificar ProyectoNucleo, Afectacion,
  Parcela, convenio, expediente, trámite ni seguimiento.

### Features nuevas y desaparecidas

La comparación de entregas requiere declarar si la nueva entrega es completa y
su alcance (proyecto, propósito y capa/universo). Una entrega parcial no acredita
la desaparición de lo omitido. El staging genera candidatos usando registros
administrativos actuales; identidad histórica confirmada es sólo una ayuda.

Los destinos confirmados en la entrega anterior que no aparecen en una nueva
entrega completa producen hallazgos de desaparición al cerrar su conciliación.
Una feature ambigua o pendiente impide concluir ausencia si podría corresponder
al destino anterior. Las versiones vigentes anteriores se conservan hasta una
decisión cartográfica explícita; no se da de baja el dominio administrativo.

Features nuevas sin destino quedan en staging como sin coincidencia y disponibles
para reconciliación tardía. No generan ProyectoNucleo ni Parcela. Los hallazgos
sin destino pueden vincularse a esas features; nunca se inventa una identidad
administrativa mediante intersección.

La idempotencia existente usa `(proyecto, propósito, SHA, pipeline, SRID)` entre
importaciones activas. Se mantiene SHA igual/configuración igual como mismo
procesamiento; SHA distinto admite una nueva entrega. Una política técnica nueva
debe quedar en la versión de pipeline/configuración para no reutilizar resultados
calculados con reglas distintas.

## 9. Endpoints y archivos de esta entrega

No se crearon ni modificaron endpoints. Los de configuración, staging, candidatos,
decisiones, resumen, geometría y finalización ya estaban en el trabajo local 024.

Pendientes, después de integrar el esquema: POST reconciliar y GET conciliaciones
bajo `/api/importaciones/{id}`, GET revisiones bajo proyecto/detalle y POST
resolver una revisión. Se reutilizarán rutas/controles existentes; no se añadirá
una segunda API para confirmar geometrías ni para crear SeguimientoEvento.

Archivos añadidos en esta ejecución:

- `backend/tests/test_gis_history_regressions.py`.
- `docs/INFORME_AUDITORIA_HISTORIA_GIS_2026-10-05.md`.

El resto del estado Git es trabajo preexistente. Su contenido se preserva.

## 10. Pruebas y resultados

Las cuatro regresiones nuevas ejecutan: núcleo con tres versiones, parcela con
tres versiones y trazabilidad; relaciones DDV A=(sí,sí), B=(sí,no), C=(no,sí),
conservando dominio y versiones de núcleos; y la historia administrativa completa
inicio→suspensión→reapertura→cambio_alcance→cierre→reapertura.

Las pruebas GIS comparan conteos de Proyecto, ProyectoNucleo, NucleoAgrario,
Parcela, Afectacion, Convenio, TramiteRan, sus eventos, SeguimientoEvento, unidades,
vínculos y expediente; también comparan filas y superficies/auditoría de los
registros administrativos involucrados. La confirmación de reemplazo sin aceptar
advertencias se rechaza sin agregar decisiones. Las geometrías anteriores se
comparan por EWKB para verificar que su contenido no fue sobrescrito, no para
clasificar cambios espaciales.

Se usa `APP_ENV=test`, `DB_NAME=software_pa_test`,
`TEST_ALLOW_DATABASE=software_pa_test`, conexión runtime y datos sintéticos.
Al faltar credenciales TEST_ADMIN en el entorno, se generó una cuenta sintética
mediante el fixture administrativo de pytest, sin mostrar contraseñas.

| Ejecución | Passed | Failed | Skipped | Warnings |
|---|---:|---:|---:|---:|
| Regresiones nuevas | 4 | 0 | 0 | 1 |
| Suite completa, 410 tests, 533.93 s | 409 | 0 | 1 | 1 |

La suite completa incluye 024, DDV, núcleo/parcela GIS, conciliación, CRS,
auth/RBAC, dominio, SeguimientoEvento, RAN, reporting, mapa y endpoints legacy.
El warning en ambas ejecuciones es la deprecación existente de Starlette
TestClient/httpx. El skipped es `test_cannot_demote_the_last_active_admin`:
el test requiere un único administrador activo y la base aislada tiene varios.

Se ejecutaron los 12 contratos SQL existentes con guarda de base y
`ON_ERROR_STOP`, usando exclusivamente `software_pa_test`: **10 passed,
2 failed**. Pasaron 002, 003, 004, 005, 006, 007, 019, **020, 021 y 024**.
Los dos fallos son de contratos históricos incompatibles con extensiones
posteriores del esquema/reporting:

- **001:** exige exactamente 51 tablas funcionales; el esquema actual contiene
  58 según ese mismo filtro. El contrato no admite las tablas agregadas después.
- **008:** informa «El indicador legado fifonafe cambió». La consulta diagnóstica
  reproduce exactamente su diferencia: 9500 filas faltantes, todas de proyectos
  inactivos; cero faltantes de proyectos activos y cero filas extra. La migración
  015 excluye explícitamente esos proyectos del read-model actual, mientras
  `vw_hito_seguimiento_007` conserva su universo legado. La prueba 008 no incorpora
  esa exclusión posterior. No se cambió la vista ni el contrato para ocultarlo.

Ambos fallos quedan reportados; no se afirma que todos los contratos SQL pasaron.
Actualizar o delimitar los contratos históricos para el esquema actual es trabajo
pendiente, separado del conflicto 020 y de la extensión GIS.

Verificación final: `git diff --check` correcto. También se comprobó whitespace
de los dos archivos nuevos mediante `git diff --no-index --check`. El snapshot
SHA-256 inicial confirma **cero cambios de contenido en todos los archivos
preexistentes auditados**, incluidas las migraciones. El ledger 020–024 conserva
los mismos checksums y no se agregó ninguna versión. `git diff --cached` vacío.

Estado final de `git status --short`:

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
?? backend/tests/test_gis_history_regressions.py
?? backend/tests/test_gis_preflight_024.py
?? docs/DERECHOS_COLECTIVOS_PARA_FRONTEND.md
?? docs/INFORME_AUDITORIA_HISTORIA_GIS_2026-10-05.md
?? docs/INFORME_CONCILIACION_GIS_2026-10-05.md
?? docs/INFORME_DERECHOS_COLECTIVOS_2026-10-02.md
```

Sólo el archivo de regresiones GIS/historia y este informe se añadieron en esta
ejecución. Los otros archivos de la lista ya estaban modificados o sin seguimiento.

No se escribieron pruebas que simulen que los endpoints de reconciliación/revisión
inexistentes ya funcionan. Las pruebas de ciclo 1→2, revisiones automáticas,
resolución/vínculo de evento, tolerancias y nueva/desaparecida como revisiones
quedan pendientes junto con su migración e implementación.

## 11. Decisiones antes de commit

Resolver primero la estrategia de integración de la 020 incompatible y la cadena
canónica, verificar los entornos con historiales distintos y asignar después la
migración de extensión. No hacer commit de esta fase como implementación completa
de reconciliación tardía/revisiones: sólo auditoría, diseño y regresiones existentes.
