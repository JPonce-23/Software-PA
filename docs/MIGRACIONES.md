# Gestión de Migraciones de Base de Datos — SOFTWARE-PA

> **Autoridad:** Documentación canónica del versionado del esquema de base de datos en PostgreSQL 15 / PostGIS.  
> **Esquema ejecutable vigente:** **025** (`GET /health` reporta el máximo registrado en `schema_migrations` de cada base).
> **Siguiente migración disponible:** **026** (reservada; no creada).

---

## 1. Principios de Operación y Versionado

1. **Secuencia lineal e inmutable:**  
   Las migraciones se ejecutan de manera ascendente mediante archivos `NNN_*.sql`. Toda migración aplicada es inmutable. La adopción excepcional de linaje descrita al final conserva los originales y cambia únicamente metadatos de versión; no autoriza modificaciones funcionales.
2. **Verificación de integridad por Checksum:**  
   El runner oficial (`backend/scripts/run_migrations.sh`) calcula el hash criptográfico SHA-256 de cada archivo `.sql`. Si un archivo ya registrado en `public.schema_migrations` sufre alteraciones en su contenido, el proceso de arranque se detiene de inmediato con error.
3. **Evolución Forward-Only:**  
   Cualquier corrección, ajuste o extensión debe implementarse exclusivamente a través de una **nueva migración incremental hacia adelante** (comenzando en `026`, no creada en esta fase). No se modifican los archivos históricos `001` a `025`. La 025 conserva el contenido funcional del antiguo 024 GIS; su adopción excepcional se documenta abajo y se aplicó únicamente en `software_pa_test`.
4. **Instalación limpia:**  
   En una base de datos vacía, la ejecución de las migraciones inicia directamente en `001_baseline_v1.sql` y avanza secuencialmente hasta `025_conciliacion_gis_proyecto.sql`. Los archivos preliminares anteriores a baseline v1 no se reproducen ni forman parte del árbol de migraciones.

---

## 2. Inventario Canónico de Migraciones Vigentes (001–025)

| Versión | Archivo SQL | Checksum SHA-256 Verificado | Propósito y Contenido Principal |
|---|---|---|---|
| **001** | `001_baseline_v1.sql` | `242ffc787beb2886d36b6fb3031c25a8baddd23ce669e78488672e274c4ad7c7` | **Baseline canónico inmutable.** Instala extensión PostGIS, estructura base de tablas de dominio y soporte (52 tablas físicas iniciales y 4 vistas), constraints, funciones de autenticación/auditoría, roles de aplicación y catálogos semilla. |
| **002** | `002_cierre_fuentes_excel.sql` | `ef1165711cc6054f26921062fd4e8202ce3dc0f7623ddb8f7eac1daa8639577e` | Cierre de fuentes Excel, definición de ciclos operativos de COP, estatus de expediente y checklist documental. |
| **003** | `003_reporting_fuentes_excel.sql` | `807279889979c3e7d55e849738f2361483e8e20810614f068515e8f95aa053ba` | Estructuras de reporting periódico y compatibilidad dimensional con tableros gerenciales. |
| **004** | `004_seguimiento_funcional_excel.sql` | `7c1a470e2429b6ec6ff3bc003ae9e3324ce3d552a984904760d0deb57381de12` | Módulo de seguimiento funcional (`seguimiento_evento`), catálogos de tipos de evento y motivos, estados documentales `parcial` y `pendiente_validacion`, y requisitos documentales opcionales. |
| **005** | `005_reporting_cierre_excel.sql` | `a35faa802c5f43a3c906aae6c62b5bac4ef842f610e87a178a2e8524ed494c76` | Arquitectura de lectura en dos capas: `vw_hito_seguimiento` (deduplicación canónica en origen), `vw_reporte_avance_periodo` (15 columnas con filtros dimensionales) y `vw_dashboard_kpi` (agregación anual). |
| **006** | `006_ajustes_reporting_post_auditoria.sql` | `e1a603fd2015615671c0cd072a0a795f50e92e8c21e838f26d88abec25dddee4` | Ajustes forward-only post auditoría: asamblea ordinaria con tipo COP propio, desacoplamiento del indicador de retiro de fondos, validación estricta de la cadena de 4 oficios FIFONAFE y vista `vw_reporte_snapshot_actual`. |
| **007** | `007_convenios_impactos_precision.sql` | `adabd7775fb8165a1db8be04a93e7971fe207e745b410c57eb6fc76cc3a7e4f7` | Precisión de hasta 7 decimales en superficies de afectación, trazabilidad de montos e impactos, y vista de cobertura. |
| **008** | `008_fifonafe_evolucion_forward_only.sql` | `95bf328f18112933481488c59763df6a6467d8fd3db354bb7e5465c727c8f012` | Evolución formal de FIFONAFE: soporte para intervinientes, acreditación de integrantes ORV y preservación de trámites versión 1. |
| **009** | `009_bitacora_append_only.sql` | `ef85729089cc0b5d3905169f87abd343a34473f7cb97717ff98b710b49f991bc` | Bitácora append-only con trigger `SECURITY DEFINER` e inmutabilidad estricta de registros de cambios. |
| **010** | `010_credenciales_auditoria.sql` | `5673767c9a24325a17ac323ed8fbfce5241dd205fd41ffccfee644709c6c6668` | Fortalecimiento de auditoría de acceso y control de credenciales. |
| **011** | `011_auditoria_actor_update.sql` | `f28b2705694fb8a011f943a81376c687cba380474aa37cbad31cc524e010df5d` | Auditoría obligatoria de actor en operaciones `UPDATE` que no proceden de scripts del sistema. |
| **012** | `012_correccion_snapshot_tuc_triestado.sql` | `c76d2d2af326a23427ae1aaf7358fdbc62faf31d91380758f744e8c8d72a7c01` | Semántica triestado para tierras de uso común en `vw_reporte_snapshot_actual`: `afecta_tuc = false` sólo cuenta en no afecta TUC si `tuc_revision_pendiente = false`; `NULL` nunca equivale a false ni a cero. |
| **013** | `013_pagos_en_reporting.sql` | `315194e6daa7b8bffd27c8d678b6e86c0486eaf851f58aba3722e90e19a37eef` | Representación canónica de pagos en reporting (`vw_hito_seguimiento`, `vw_reporte_avance_periodo`, `vw_dashboard_kpi`) a través de la cadena `Pago → Indemnizacion → Afectacion → ProyectoNucleo → Proyecto`. |
| **014** | `014_convenios_colectivos_por_destino.sql` | `0ac8df3e32cc5bb7a103a314160fa4b6b392d9e5e041af3aaa74c0cda9aeceab` | Read-model `vw_convenio_colectivo_destino` con granularidad `id_convenio + destino_superficie`. Separa superficie física de superficie declarada y establece que `monto_declarado` es un atributo **NO ADITIVO**. |
| **015** | `015_exclusion_proyectos_inactivos.sql` | `4e5d7fa8926f8026923146d3a0695d933bb43e9bb5f8c71ef8f9ecd9bae4b422` | Corrección forward-only de read-models para excluir estrictamente proyectos con `activo IS NOT TRUE` de `vw_reporte_snapshot_actual`, `vw_hito_seguimiento`, `vw_reporte_avance_periodo`, `vw_dashboard_kpi` y `vw_convenio_colectivo_destino`. |
| **016** | `016_normalizacion_convenio_superficie_adicional.sql` | `246eb8247d1f3256e40453afa5f5d13d09586d90f0d3e599680ed8865160c810` | Normaliza la representación de convenios y superficies adicionales. |
| **017** | `017_normalizar_contexto_asamblea_adicional.sql` | `7fe91d37c1724291f0bf3fa47ba58d6afff8c062e6c44d527b14ea025fa36282` | Normaliza el contexto de asambleas relacionadas con superficies adicionales. |
| **018** | `018_orv_persona_ciclo_vida.sql` | `2fb5676b52d902b636b3941490ea71a8044a791764b2913a18b6a905d9ddfea3` | Formaliza el ciclo de vida de integrantes ORV y protege las relaciones activas de personas. |
| **019** | `019_catalogo_nucleos_ran.sql` | `6769168eb11b2773b4e8e42f9409ccbbfbe986984f69895a562fe17c29f03b04` | Convierte la coincidencia municipio/tenencia/nombre en índice de búsqueda no único y establece la identidad externa única `fuente_datos + id_nucleo_fuente`; exige procedencia completa para filas RAN/PHINA. No carga el CSV ni altera `ProyectoNucleo`. |
| **020** | `020_auditoria_heartbeat_sesion.sql` | `cfa4dadb2e8b5bb9b8cddddf617c34132380ad49a660de9037de43850263f4c8` | Canónico de backend-logica: omite heartbeat de sesión tras validar actor; conserva expiración correlacionada, auditoría de cambios simultáneos y redacción de secretos. |
| **021** | `021_derecho_via_proyecto.sql` | `c759eaab96a7ed88679fd5fa288504b4bdf36724479d82e155044a572da90d4e` | Crea el DDV poligonal `MULTIPOLYGON` 4326 por proyecto, con versiones históricas, una sola versión `es_vigente`, auditoría y baja lógica. Conserva `trazo_proyecto` como legacy. |
| **022** | `022_importacion_ddv_gpkg.sql` | `40e988e06f7f211995ea62456ee7fc64e951fabd2ff14609f155de968171d58f` | Amplía el staging a `derecho_via_proyecto`, exige GPKG sin mapeo para este objetivo y valida el destino DDV por proyecto; conserva los objetivos legacy. |
| **023** | `023_importacion_nucleos_gpkg.sql` | `ede1ea43947cec0f9f9ba433319d69de21847c892985adbd03feed80ef0f051b` | Habilita `nucleo_agrario_gpkg` como objetivo de staging distinto del legacy, exige GPKG sin mapeo y valida que el destino sea un núcleo RAN activo vinculado activamente al proyecto. |
| **024** | `024_importacion_parcelas_gpkg.sql` | `15f36ea78a591aeb0f587a84e7e2bddb21f53de455d80daaf8532422796bc2d6` | Habilita `parcela_gpkg` como objetivo de staging separado del legacy, exige GPKG sin mapeo y valida que el destino sea una parcela activa de un núcleo RAN activo vinculado al proyecto. No altera el índice de identidad parcelaria. |
| **025** | `025_conciliacion_gis_proyecto.sql` | `8338aace95845761acf0f9b675064ca25a6b0da2117013178ed060f260ec372a` | Conciliación explícita contra destinos administrativos del proyecto; geometrías por proyecto, candidatos y decisiones auditadas; CRS configurable, trazabilidad WKB/Z e idempotencia por pipeline/CRS. Conserva las geometrías globales legacy y no crea entidades administrativas. |

---

## 3. Procedimiento de Ejecución y Aplicación

El script `backend/scripts/run_migrations.sh` es la herramienta estándar para aplicar y verificar migraciones en cualquier entorno.

### 3.1 Flujo automático en contenedor

Al iniciar el contenedor `db`, los scripts de inicialización invocan el runner automáticamente:
```bash
# Inicialización y ejecución automática
docker compose up -d db
```

### 3.2 Ejecución manual del runner

Para ejecutar o verificar migraciones manualmente desde la computadora anfitriona o en un pipeline de integración continua:

```bash
# Cargar variables de entorno
set -a; source .env; set +a

# Ejecutar el runner de migraciones
docker compose exec -T backend bash scripts/run_migrations.sh
```

El script realiza los siguientes pasos para cada archivo `NNN_*.sql`:
1. Valida el formato del nombre del archivo.
2. Calcula el checksum SHA-256 local.
3. Consulta la tabla `public.schema_migrations`.
4. Si ya fue aplicada, verifica que el checksum coincida exactamente. Si difiere, aborta la ejecución para prevenir inconsistencias.
5. Si no ha sido aplicada, la ejecuta dentro de una transacción única (`--single-transaction`) y registra la versión, nombre y checksum en `schema_migrations`.

### 3.3 Verificación del Estado del Esquema

Puede comprobarse el esquema vigente mediante una llamada HTTP simple:

```bash
curl --fail http://localhost:8000/health
```

Respuesta esperada:
```json
{
  "status": "ok",
  "schema": 25
}
```

O directamente mediante consulta SQL:
```sql
SELECT version, nombre, aplicada_en 
FROM public.schema_migrations 
ORDER BY version::integer DESC;
```

### 3.4 Catálogo nacional RAN/PHINA

La migración 019 prepara la identidad del catálogo maestro, pero no carga datos. El importador `backend/scripts/import_catalogo_nucleos_ran.py` lee el CSV oficial como Windows-1252, calcula SHA-256, cruza la clave municipal INEGI y resuelve la tenencia por código de catálogo. El modo predeterminado es dry-run:

```bash
docker compose exec -T -e DB_NAME=software_pa_test backend \
  python scripts/import_catalogo_nucleos_ran.py /app/ruta/catalogo.csv \
  --dry-run --expected-database software_pa_test
```

Sólo después de obtener cero errores y cero municipios sin correspondencia puede usarse `--apply`. La aplicación exige nombrar la base esperada y un usuario activo responsable de auditoría:

```bash
docker compose exec -T -e DB_NAME=software_pa_test backend \
  python scripts/import_catalogo_nucleos_ran.py /app/ruta/catalogo.csv \
  --apply --expected-database software_pa_test --actor-user-id ID_USUARIO
```

La carga es transaccional e idempotente, conserva `id_nucleo` en actualizaciones y no elimina núcleos ausentes de archivos posteriores. El catálogo mejora la identificación maestra de `NucleoAgrario`; no reemplaza el vínculo operativo Excel-First de `ProyectoNucleo`.

### 3.5 Derecho de Vía poligonal

La migración 021 agrega `derecho_via_proyecto` sin migrar ni eliminar `trazo_proyecto`. Para cada proyecto se conservan versiones numeradas; `es_vigente` selecciona como máximo una. Al promover una versión, la operación debe desmarcar la anterior y marcar la nueva dentro de la misma transacción. Una versión que deja de estar vigente conserva `activo = true`; `activo = false` corresponde exclusivamente a baja lógica con usuario, fecha y motivo. La geometría obligatoria debe ser un `MULTIPOLYGON` válido y no vacío en SRID 4326.

### 3.6 Importación DDV GeoPackage

La migración 022 habilita el objetivo `derecho_via_proyecto` en las tablas de staging existentes. Impone `formato_detectado = 'gpkg'`, mapeos vacíos y destino EPSG:4326 sólo para este objetivo; los objetivos legacy conservan su contrato. El endpoint `POST /api/proyectos/{id_proyecto}/geoespacial/ddv/importaciones` recibe exclusivamente `archivo` `.gpkg`, `fuente` y `fecha_fuente` opcional. El preflight exige driver GeoPackage, una capa, features y CRS identificable. Desde 025, «una capa» significa exactamente una capa espacial de datos; `layer_styles` no cuenta. Los GET de importación/features y `POST /api/importaciones/{id_importacion}/confirmar` se reutilizan para preview y confirmación. La confirmación bloquea importación y proyecto, une las geometrías poligonales en un MultiPolygon y actualiza las versiones DDV en una transacción. Las advertencias de reparación exigen `aceptar_advertencias = true`; los errores impiden confirmar. `/mapa` y `trazo_proyecto` siguen usando su flujo legacy.

### 3.7 Contrato histórico 023 de núcleos (sustituido por 025)

La migración 023 incorpora únicamente el objetivo de staging `nucleo_agrario_gpkg`, separado de `nucleo_agrario` legacy. El endpoint `POST /api/proyectos/{id_proyecto}/geoespacial/nucleos/importaciones` exige GPKG de una capa, `cve_unica` y polígonos con CRS identificable; no admite mapeo ni identificadores internos. Resuelve la clave contra `RAN_PHINA_CATALOGO_NUCLEOS + id_nucleo_fuente` y verifica núcleo y vínculo `proyecto_nucleo` activos. La previsualización almacena `registro_destino_id`, hash de geometría previa y advertencias de reparación o reemplazo, sin modificar el dominio. La confirmación reutiliza `POST /api/importaciones/{id_importacion}/confirmar`, bloquea importación, vínculos y núcleos, revalida estado e identidad, y actualiza geometría y procedencia en una transacción. Una clave inexistente, duplicada en el archivo, inactiva o fuera del proyecto impide confirmar todo el lote. La unicidad del índice `uq_nucleo_identidad_fuente` impide ambigüedad en un esquema sano; el resolvedor mantiene una comprobación defensiva.

### 3.8 Contrato histórico 024 de parcelas (sustituido por 025)

La migración 024 añade sólo el objetivo `parcela_gpkg` al staging y conserva el índice `uq_parcela_numero_normalizado` sin cambios. `POST /api/proyectos/{id_proyecto}/geoespacial/parcelas/importaciones` exige GPKG estricto de una capa, `cve_unica_nucleo` y `no_parcela`, sin mapeo ni identificadores internos. En staging se resuelve primero el núcleo RAN/PHINA activo y vinculado al proyecto; después `id_nucleo + no_parcela` identifica una parcela existente y activa. El valor original queda en `atributos_originales`, el canónico en `atributos_normalizados` y el destino en `registro_destino_id`. La normalización coincide con el índice vigente en espacios y caja, y sólo añade la equivalencia documentada `P.-<dígitos> → P-<dígitos>`; conserva sufijos como `P-585A/B/C/D` y otros signos. Si hay dos candidatas, se registra error de ambigüedad. La confirmación bloquea importación, vínculos, núcleos y parcelas; revalida identidad y geometría previa, exige aceptación de advertencias para reparaciones/reemplazos y actualiza geometría y procedencia en una única transacción. No crea parcelas ni modifica superficies administrativas.

### 3.9 Conciliación GIS por proyecto — 025

Los contratos descritos en 3.7 y 3.8 documentan el desarrollo histórico. El código vigente utiliza `conciliacion-v2`: una clave oficial es opcional y una coincidencia nunca escribe automáticamente la geometría. Las importaciones poligonales anteriores en staging deben reprocesarse; sus datos no se borran. Los endpoints de creación, consulta y finalización se reutilizan, con decisiones explícitas por feature antes de finalizar.

La migración crea `proyecto_configuracion_gis`, `proyecto_nucleo_geometria`, `proyecto_parcela_geometria`, `importacion_feature_candidato` e `importacion_feature_decision`, y la vista `vw_gis_parcela_proyecto`. Esta última exige la cadena administrativa activa `ProyectoNucleo → Afectacion → AfectacionUnidadAgraria → UnidadAgraria → Parcela`; una parcela que sólo pertenece al mismo núcleo no es destino del proyecto.

Amplía el staging con geometría original y de trabajo, CRS, dimensión, estado de conciliación y versión del pipeline. Amplía DDV con importación, SHA y geometría/CRS de trabajo. Incluye FKs tipadas, GiST, unicidad de selección/destino por importación, unicidad de versión vigente, auditoría, decisiones append-only, guardas de proyecto/CRS y RBAC. No modifica `021–024` ni traslada datos legacy.

En esta entrega sólo se aplicó a `software_pa_test`, después de `SELECT current_database()`, con `APP_ENV=test`, `DB_NAME=software_pa_test` y `TEST_ALLOW_DATABASE=software_pa_test`. No se aplicó a `db_pruebas_alfredo` ni se creó otra base. El contrato `backend/db/tests/025_conciliacion_gis_proyecto_contract.sql` comprueba esquema, índices, FKs, legado, ausencia de pertenencia por intersección y precisión; se ejecuta con rollback y rechaza cualquier base distinta de `software_pa_test`.

La política de CRS, el inventario real de los cuatro GPKG y la validación están en [INFORME_CONCILIACION_GIS_2026-10-05.md](INFORME_CONCILIACION_GIS_2026-10-05.md).


## RECONCILIACIÓN EXCEPCIONAL DEL LINAJE GIS

La rama GIS nació en `cf07d7ea519794ee558229de88681c05e9e0fa01` y utilizó
020–024 antes de incorporar la 020 heartbeat de la línea base backend-logica.
Esta colisión no se resuelve reejecutando DDL ni desactivando checksums.
El remoto incorporado es `49f12f747a1eda4fc75930d78e0f23dd00baf422`;
el HEAD GIS de origen es `a829f1c631e4ee56c0ce26edcb3615ceaf5d61f8`.

Los SQL originales inmutables se conservan en `backend/db/lineage/gis_precanonical/`,
fuera del directorio ejecutable. `gis_lineage_manifest.json` congela versiones,
nombres, SHA antiguos/canónicos y hashes del cuerpo funcional. La firma aprobada
`gis_legacy_schema_signature.json` incluye estructuras, funciones, restricciones,
permisos y metadata geométrica sin consultar `geometry_columns` ni guardar datos
personales. El script fija además los hashes de ambos manifiestos.

| Antiguo | Canónico | SHA antiguo | SHA canónico |
|---|---|---|---|
| 020 derecho_via_proyecto | 021 | `3662cc9ce0ed2e63095b7a873616356aa965e94b1b34e9f651ffd5396452dc09` | `c759eaab96a7ed88679fd5fa288504b4bdf36724479d82e155044a572da90d4e` |
| 021 importacion_ddv_gpkg | 022 | `16f63229569574f078105423a1a914c1621b6662150dfc090124f60817b719f6` | `40e988e06f7f211995ea62456ee7fc64e951fabd2ff14609f155de968171d58f` |
| 022 importacion_nucleos_gpkg | 023 | `a244ed434176feff02ceacbb0e5204bebe0bb16d582dbb4efdea9a13a41ebf0b` | `ede1ea43947cec0f9f9ba433319d69de21847c892985adbd03feed80ef0f051b` |
| 023 importacion_parcelas_gpkg | 024 | `6491328bf6da3f22af31e1ae93e4569ba3836493043748d40cbc23fe26d3a7dd` | `15f36ea78a591aeb0f587a84e7e2bddb21f53de455d80daaf8532422796bc2d6` |
| 024 conciliacion_gis_proyecto | 025 | `c1a6684b06682ba63a9ad090c561d1cf2b9fee5b0fc1ce0da7f6c0a7952399c4` | `8338aace95845761acf0f9b675064ca25a6b0da2117013178ed060f260ec372a` |

### Procedimiento manual autorizado

Se requiere mantenimiento: sin runner ni escritores de aplicación concurrentes.
La única base persistente admitida es `software_pa_test`; se exigen
`APP_ENV=test`, `DB_NAME=software_pa_test`, `TEST_ALLOW_DATABASE=software_pa_test`
y credenciales administrativas explícitas, nunca las del rol runtime.

```bash
python backend/scripts/reconcile_gis_migration_lineage.py --dry-run --expected-database software_pa_test
python backend/scripts/reconcile_gis_migration_lineage.py --apply --expected-database software_pa_test
```

El modo predeterminado es dry-run en una transacción de sólo lectura. Sólo admite
el estado antiguo exacto 001–024 con firmas coincidentes. Apply adquiere un advisory
lock estable, bloquea el ledger, protege los datos comparados y revalida todo.
Actualiza 024→025, 023→024, 022→023, 021→022, 020→021, cambiando versión/nombre/SHA
y preservando `aplicada_en`. Comprueba que no cambió ningún dato ni esquema antes
del commit. Todo fallo previo al commit revierte la transacción completa.

El estado resultante es `RECONCILED_PENDING_HEARTBEAT`: 24 filas, 020 ausente.
Consultar directamente el ledger; `/health` por sí solo no acredita finalización.
Ejecutar después el runner oficial con conexión explícita a `software_pa_test`:
aplica 020 heartbeat y verifica por SHA las GIS 021–025, sin repetir su DDL.
El estado completo contiene exactamente 001–025.

La reejecución del reconciliador sobre un estado pendiente o canónico aborta sin
escribir. Estados incompletos/desconocidos también abortan. Un resultado incierto
del COMMIT se clasifica mediante una nueva lectura y exige verificación manual;
no se intenta reparar. Tras aplicar heartbeat no se revierte únicamente el ledger.

La evidencia inicial y las firmas/counts sin datos personales se guardan localmente
en `backups/lineage_gis_20261005/` (ignorado por Git). La prueba reproducible
`backend/scripts/test_gis_lineage_equivalence.py` instala A limpio y B antiguo→
reconciliador→runner, compara esquema completo y ledger lógico, comprueba fechas y
datos, y ejecuta las pruebas de rollback/concurrencia. Usa `lineage_compose.yml`,
una instancia tmpfs sin puertos con DB `software_pa_test`, eliminada incluso al fallar.

Esto es una adopción excepcional de un linaje conocido, **no un procedimiento
ordinario de migración ni una herramienta para reparar bases desconocidas**.

Los contratos históricos 001/008 se adaptan exclusivamente en tests: baseline
obligatorio en lugar de conteo global y universo legado activo según 015. Los SQL
001/008 y el reporting productivo permanecen intactos. La renumeración no añade
026, reconciliación tardía, revisiones GIS ni cambios administrativos.

El contrato 001 verifica también dependencias transitivas de reporting, ya que
005 y posteriores introdujeron vistas intermedias. La regresión sintética 007
aporta `id_tipo_fin` cuando 018 está aplicada, sin alterar sus aserciones ni
las migraciones de dominio.
