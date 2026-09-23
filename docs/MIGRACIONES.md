# Gestión de Migraciones de Base de Datos — SOFTWARE-PA

> **Autoridad:** Documentación canónica del versionado del esquema de base de datos en PostgreSQL 15 / PostGIS.  
> **Esquema ejecutable vigente:** **015** (`GET /health` reporta `{"status": "ok", "schema": 15}`).  
> **Siguiente migración disponible:** **016**.

---

## 1. Principios de Operación y Versionado

1. **Secuencia lineal e inmutable:**  
   Las migraciones se ejecutan de manera ascendente mediante archivos `NNN_*.sql`. Toda migración aplicada es inmutable: su contenido no debe editarse bajo ninguna circunstancia.
2. **Verificación de integridad por Checksum:**  
   El runner oficial (`backend/scripts/run_migrations.sh`) calcula el hash criptográfico SHA-256 de cada archivo `.sql`. Si un archivo ya registrado en `public.schema_migrations` sufre alteraciones en su contenido, el proceso de arranque se detiene de inmediato con error.
3. **Evolución Forward-Only:**  
   Cualquier corrección, ajuste o extensión debe implementarse exclusivamente a través de una **nueva migración incremental hacia adelante** (comenzando en `016`). No se modifican los archivos históricos `001` a `015`.
4. **Instalación limpia:**  
   En una base de datos vacía, la ejecución de las migraciones inicia directamente en `001_baseline_v1.sql` y avanza secuencialmente hasta `015_exclusion_proyectos_inactivos.sql`. Los archivos preliminares anteriores a baseline v1 no se reproducen ni forman parte del árbol de migraciones.

---

## 2. Inventario Canónico de Migraciones Vigentes (001–015)

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
  "schema": 15
}
```

O directamente mediante consulta SQL:
```sql
SELECT version, nombre, aplicada_en 
FROM public.schema_migrations 
ORDER BY version::integer DESC;
```
