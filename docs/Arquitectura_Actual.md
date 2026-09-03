# Arquitectura actual de SOFTWARE-PA

> Rama: `feature/backend-logica`
> Esquema vigente para instalaciones nuevas: Baseline V1 (`001_baseline_v1.sql`)
> Última validación: 2026-09-03

## 1. Alcance

SOFTWARE-PA administra la liberación de derecho de vía sobre propiedad social. El contexto funcional central es `proyecto_nucleo`, que relaciona un proyecto con un núcleo agrario. El baseline contiene 51 tablas funcionales, cuatro vistas propias y PostGIS.

No existe `bien_afectado`. El baseline tampoco conserva columnas, funciones o triggers cuyo único propósito era sincronizar el modelo histórico 001–039.

## 2. Modelo canónico

```text
Proyecto
├── UsuarioProyecto (RBAC)
├── TrazoProyecto (GIS)
└── ProyectoNucleo
    ├── ProyectoNucleoReferencia
    ├── ProyectoNucleoResponsable
    ├── ActividadCampo
    ├── Afectacion
    │   └── AfectacionUnidadAgraria N:M
    ├── Asamblea
    │   ├── AsambleaConvocatoria 1:N
    │   └── TramiteRan 1:N → TramiteRanEvento 1:N
    ├── Convenio
    │   ├── ConvenioAfectacion
    │   ├── ConvenioCompareciente
    │   └── TramiteRan 1:N → TramiteRanEvento 1:N
    ├── TramiteFifonafe
    │   ├── TramiteFifonafeAfectacion
    │   └── TramiteFifonafeEvento 1:N
    └── Afectacion → Indemnizacion → Pago

NucleoAgrario
├── PadronHistorial
├── ORV
│   ├── OrvIntegrante
│   └── TramiteRan 1:N → TramiteRanEvento 1:N
├── Parcela → ParcelaTitular
└── UnidadAgraria
    └── UnidadAgrariaTitular
```

Fuentes únicas:

- tenencia y residencia: `catalogo_operativo`;
- responsable: `proyecto_nucleo_responsable`;
- convocatoria y celebración: `asamblea_convocatoria`;
- seguimiento RAN: `tramite_ran` y `tramite_ran_evento`;
- oficios FIFONAFE: `tramite_fifonafe_evento`;
- unidades afectadas: `unidad_agraria` y `afectacion_unidad_agraria`;
- titulares: `unidad_agraria_titular` o `parcela_titular`, según el vínculo;
- estado registral del ORV: `orv.id_estado_registral`.

Las superficies de `afectacion` son totales administrativos. Las superficies de `afectacion_unidad_agraria` pertenecen a cada unidad; no se fuerza igualdad automática.

## 3. RAN, asambleas y FIFONAFE

`tramite_ran` conserva `id_proyecto_nucleo` para objetivos Asamblea/Convenio e `id_nucleo` para ORV. `chk_tramite_ran_contexto` y `trg_tramite_ran_contexto` garantizan exactamente un objetivo y coherencia entre objetivo y contexto. La cardinalidad es 1:N por objetivo.

`asamblea` no almacena fechas de convocatoria ni `fecha_realizada`. Una asamblea celebrada se deriva de la única convocatoria activa con `fecha_realizacion`; la unicidad parcial evita ambigüedad.

`convenio` contiene sólo información del instrumento jurídico. No contiene resúmenes RAN.

`tramite_fifonafe` contiene estado, acuse y resultado propios. Los oficios repetibles se almacenan sólo en `tramite_fifonafe_evento`.

## 4. Documentos e importaciones

`documento`, `documento_version`, `documento_vinculo`, `requisito_documental` y `expediente_requisito` mantienen responsabilidades distintas. Las versiones son inmutables y los objetivos documentales se validan mediante tipos canónicos; `bien_afectado` no es un target.

La importación tabular usa `importacion_tabular` e `importacion_tabular_celda` para conservar celda, fila, columna y valor original. La importación geoespacial usa `importacion_archivo` e `importacion_feature`, con geometría PostGIS y staging por feature. Ambos flujos permanecen separados.

## 5. Seguridad y auditoría

`usuario`, `usuario_proyecto`, `sesion_usuario`, `estado_autenticacion_usuario`, `evento_acceso` y `bitacora` separan identidad, alcance RBAC, sesiones, bloqueo, eventos inmutables y cambios de dominio.

Roles:

- owner/bootstrap: identidad indicada en `POSTGRES_ADMIN_USER`;
- `software_pa_app`: rol `NOLOGIN` con `SELECT/INSERT/UPDATE`;
- `pa_runtime` o `DB_RUNTIME_USER`: LOGIN miembro únicamente de `software_pa_app`.

Runtime no posee objetos, no tiene DDL, `DELETE`, `TRUNCATE` ni escritura en `schema_migrations`. Las contraseñas se provisionan por entorno fuera del SQL.

## 6. Vistas

- `vw_proyecto_nucleo_resumen`: residencia/tenencia catalogadas, responsable principal, referencia principal y agregaciones previas por contexto.
- `vw_dashboard_kpi`: agrega convocatorias, RAN, FIFONAFE, unidades, superficies administrativas, convenios, indemnizaciones y pagos desde fuentes canónicas.
- `vw_orv_estado`: estado y vigencia del ORV a partir de `orv.id_estado_registral` y fechas propias.
- `vw_convenio_tipo_cop_operativo`: etiqueta operativa derivada de tipo jurídico y consecutivo.

## 7. Integridad y triggers

El baseline conserva únicamente:

- auditoría de altas/cambios funcionales;
- prevención de borrado físico en entidades con historial;
- inmutabilidad de eventos de acceso y versiones documentales;
- coherencia de contexto y objetivos;
- reglas vigentes de convenio, afectación, FIFONAFE, catálogos y GIS.

No hay triggers de proyección hacia campos legacy.

## 8. Instalación y evolución

`schema_migrations` registra versión, nombre, SHA-256 y fecha. Una base vacía se crea con `001_baseline_v1.sql`; la siguiente migración será `002`. El runner rechaza cambios en archivos ya aplicados.

Las migraciones incrementales anteriores 001–039 permanecen sólo en Git. Los documentos bajo `docs/historico`, `docs/propuestas` y `docs/evaluaciones` no son instrucciones de instalación vigentes.

## 9. API y frontend

FastAPI usa modelos SQLAlchemy alineados con el baseline y Pydantic rechaza campos desconocidos. Las incompatibilidades que debe adaptar el frontend se enumeran en [API_CAMBIOS_BASELINE_V1.md](backend/API_CAMBIOS_BASELINE_V1.md). Ningún archivo de `frontend/` fue modificado por este cambio.
