# Diseño de reestructuración de base de datos: modelo ProyectoNucleo / Parcela

> Fecha: 2026-08-25  
> Rama auditada: `feature/backend-logica`  
> Estado: **APROBADO PARA IMPLEMENTAR REESTRUCTURACIÓN**  
> Alcance de este documento: diseño técnico. No contiene SQL definitivo y no implica que el modelo ya esté implementado.

## 1. Decisión ejecutiva

Se elige **Opción B: reset controlado de datos de prueba, reconstrucción del dominio y seed nuevo**.

La historia `001`-`030` se conserva. El refactor se implementará con tres migraciones nuevas, iniciando en `031`; no se hará backfill de datos funcionales, dual-write, sincronización entre modelos ni preservación de IDs de prueba. Después de estabilizar y validar el refactor será conveniente preparar, en una tarea separada, una baseline limpia para instalaciones nuevas.

El modelo canónico queda centrado en:

```text
Proyecto
├── TrazoProyecto (cartográfico)
└── ProyectoNucleo
    └── NucleoAgrario
        ├── ORV / Padrón / ActividadCampo
        ├── Asamblea colectiva -> RAN del acta
        ├── Afectacion colectiva
        └── Parcela -> Afectacion individual

Afectacion(s) <- ConvenioAfectacion -> Convenio
Afectacion(s) <- TramiteFifonafeAfectacion -> TramiteFifonafe
Afectacion -> Indemnizacion -> Pago(s)
```

No quedan cardinalidades funcionales importantes abiertas. La relación entre convenio y afectación es exclusivamente `convenio_afectacion`; `convenio` no tendrá `id_afectacion`.

## 2. Evidencia auditada

La rama local coincide con `feature/backend-logica` y el árbol estaba limpio al iniciar esta auditoría. Se inspeccionaron:

- las migraciones `001`-`030` y el esquema PostgreSQL efectivo;
- tablas, columnas, FK, CHECK, UNIQUE, índices, triggers, funciones y vistas;
- `backend/app/models.py`, schemas Pydantic, routers, servicios y autorización;
- navegación, formularios, mapa, administración y dashboard React;
- seeds SQL/Python, pruebas `pytest` y pruebas E2E Playwright;
- la documentación objetivo aprobada y la implementación vigente documentada;
- los tres Excel locales, en modo de sólo lectura, para seleccionar datos representativos del seed.

La base local efectiva tiene PostgreSQL 15 + PostGIS, registra las migraciones `004`-`030` en `schema_migrations` y usa `001_init_schema.sql` como bootstrap de volumen. Las versiones `002` y `003` son historia anterior a la baseline consolidada y no deben reaplicarse sobre una instalación creada con el `001` vigente.

Los catálogos efectivos contienen 32 entidades federativas y 2,478 municipios activos. El repositorio no contiene todavía un artefacto versionado completo y reproducible para esos 2,478 municipios; corregir esa carencia forma parte del gate del seed de implementación.

### 2.1 Dependencia legacy por capa

| Capa | Evidencia actual | Impacto requerido |
|---|---|---|
| SQL | `tramo_nucleo` es pivote de afectación, actividad, asamblea, convenio, FIFONAFE, minutas, bitácora y vistas. `afectacion_ciclo` se crea automáticamente. | Retirar FK, funciones de secuencia y vistas basadas en ciclo; recrear el dominio. |
| SQL espacial | Triggers usan `ST_Intersects`; funciones y vistas usan `ST_Area`; la geometría de afectación es obligatoria salvo registros Excel. | Conservar sólo validación de tipo/SRID/validez. Eliminar gates, candidatos e inferencia de superficie oficial. |
| SQLAlchemy | `Tramo`, `FranjaDerechoVia`, `SeccionDerechoVia`, `TramoNucleo`, `AfectacionCiclo`, `UsuarioTramo` y relaciones asociadas reflejan el modelo legacy. | Sustituir por modelos objetivo y relaciones canónicas. |
| Pydantic | Existen schemas `TramoNucleo*`, `AfectacionCiclo*`, `UsuarioTramo*`; convenios, asambleas y FIFONAFE exigen IDs legacy. | Versionar contratos API y eliminar campos legacy. |
| Servicios | `access.py` filtra por `usuario_tramo`; `flujo.py` aplica secuencias por ciclo; `afectaciones.py` exige intersección; servicios GIS generan candidatos. | Rehacer alcance por proyecto y reglas alrededor de hechos capturados. |
| Routers | `main.py` y routers exponen `/tramos`, `/tramos-nucleos`, ciclos, candidatos y asignaciones por tramo. | Sustituir por `/proyectos/{id}/nucleos`, recursos anidados y asignaciones por proyecto. |
| Frontend | Dashboard por tramo, lista de expedientes por tramo, subexpediente por ciclo, formularios con `id_tramo_nucleo`/`id_ciclo_afectacion`, administración y mapa por tramo. | Navegación Proyecto -> Entidad -> Municipio -> Núcleo; eliminar selector/panel de ciclo. |
| Tests | 12 módulos backend y el E2E de expedientes dependen de IDs o fixtures legacy. | Reescribir fixtures y contratos sin IDs heredados. |

La búsqueda estática encontró `tramo_nucleo` en 41 archivos con 715 referencias, `id_ciclo_afectacion` en 19 archivos con 205 referencias, `id_tramo` en 50 archivos con 871 referencias, `ST_Intersects` en 5 archivos y `ST_Area` en 5 archivos. Es un reemplazo transversal, no una modificación aislada de tablas.

### 2.2 Responsabilidades que hoy concentran los objetos legacy

| Objeto legacy | Responsabilidades actuales | Destino objetivo |
|---|---|---|
| `tramo` | Navegación, autorización, agrupación artificial y soporte de secciones GIS. | Se elimina. El proyecto agrupa; el trazo vive en `trazo_proyecto`. |
| `tramo_nucleo` | Expediente, alcance territorial, consecutivo, expropiación, no afectación de uso común y geometría de cruce. | Contexto en `proyecto_nucleo`; condiciones en la afectación u observaciones; referencias históricas en tabla hija. |
| `afectacion_ciclo` | Linaje de variantes, superficie base, secuencia, estados, límite financiero y enlace entre todos los hechos. | `tipo_convenio`, `consecutivo`, `id_convenio_padre`, `contexto_actividad` y relaciones directas. |
| `seccion_derecho_via` | Autoridad espacial por tramo y gate de intersección. | Se elimina; no existe autoridad espacial administrativa. |
| `candidato_tramo_nucleo` | Convierte intersecciones GIS en candidatos de expediente. | Se elimina sin sustitución. La alta de `proyecto_nucleo` es administrativa. |
| `usuario_tramo` | Alcance RBAC territorial. | `usuario_proyecto`. |
| `franja_derecho_via` | Trazo por proyecto mezclado con franja, ancho y vínculo residual a tramo. | `trazo_proyecto`, exclusivamente cartográfico y lineal. |

## 3. Clasificación de tablas actuales

| Tabla actual | Clasificación | Razón / destino |
|---|---|---|
| `entidad_federativa` | MANTENER | Catálogo válido; debe quedar reproducible con 32 filas. |
| `municipio` | MANTENER | Catálogo válido; debe quedar reproducible con 2,478 filas y clave INEGI completa. |
| `proyecto` | MODIFICAR | Se conserva como raíz; se normalizan columnas de auditoría y relaciones. |
| `nucleo_agrario` | MODIFICAR | Se conserva como maestro registral y su geometría sigue opcional. |
| `tramo` | ELIMINAR | No aporta una responsabilidad funcional objetivo. |
| `franja_derecho_via` | RECREAR | Sus datos útiles se representan en la nueva `trazo_proyecto`; no se conservan anchos ni FK a tramo. |
| `seccion_derecho_via` | ELIMINAR | Era autoridad espacial por tramo, concepto retirado. |
| `tramo_nucleo` | ELIMINAR | Sus responsabilidades necesarias pasan a `proyecto_nucleo` y `proyecto_nucleo_referencia`. |
| `candidato_tramo_nucleo` | ELIMINAR | La intersección no crea ni propone expedientes. |
| `usuario_tramo` | ELIMINAR | Se reemplaza por `usuario_proyecto`. |
| `persona` | MANTENER | Maestro reutilizable por titulares, ORV y beneficiarios. |
| `persona_nucleo` | ELIMINAR | No lo requiere el modelo objetivo; las relaciones necesarias son específicas. |
| `persona_fuente_legacy` | RECREAR | Se generaliza como `trazabilidad_fuente` para cualquier entidad. |
| `parcela` | RECREAR | Falta `no_parcela`, procedencia geométrica y el modelo de titular normalizado debe ser canónico. |
| `parcela_titular` | MODIFICAR | Se conserva la cardinalidad N:M; se retira `id_nucleo` redundante. |
| `orv` | MODIFICAR | Se conservan vigencias/RAN; se eliminan nombres de integrantes duplicados. |
| `orv_integrante` | MODIFICAR | Se conserva; se retira `id_nucleo` redundante y se flexibiliza la multiplicidad de cargos. |
| `padron_historial` | MODIFICAR | Se conserva como historial; fecha o cantidad pueden ser desconocidas en la fuente. |
| `actividad_campo` | RECREAR | Sensibilización y caminamiento pasan directamente a `proyecto_nucleo`, sin FK a afectación ni ciclo. |
| `afectacion` | RECREAR | Cambia de expediente legacy a `proyecto_nucleo`, elimina geometría y agrega superficies/avalúo simples. |
| `afectacion_ciclo` | ELIMINAR | No existe en el modelo objetivo. |
| `asamblea` | RECREAR | Pertenece a `proyecto_nucleo`, es exclusivamente colectiva y separa RAN del acta. |
| `convenio` | RECREAR | Se vuelve repetible, elimina ciclo y usa `convenio_afectacion` como relación canónica. |
| `tramite_fifonafe` | RECREAR | Pertenece a `proyecto_nucleo` y cubre una o más afectaciones mediante `tramite_fifonafe_afectacion`, sin duplicar oficios. |
| `pago_indemnizacion` | RECREAR | Se separa en `indemnizacion` y `pago`. |
| `documentacion_soporte` | RECREAR | Se separa metadata documental de sus vínculos y versiones. |
| `documento_version` | MODIFICAR | Se conserva el versionado inmutable bajo `documento`. |
| `minuta` | ELIMINAR | No está en el modelo aprobado; observaciones y soportes cubren la evidencia requerida. |
| `acuerdo` | ELIMINAR | Depende de minuta y no tiene evidencia suficiente como módulo objetivo. |
| `alertas` | ELIMINAR | No es fuente de verdad ni requisito objetivo; las fechas alimentarán vistas/reportes. |
| `alertas_vistas` | ELIMINAR | Depende del módulo de alertas retirado. |
| `usuario` | MANTENER | Se conserva autenticación, roles y baja lógica. |
| `estado_autenticacion_usuario` | MANTENER | Bloqueo e intentos fallidos siguen vigentes. |
| `sesion_usuario` | MANTENER | Sesiones revocables siguen vigentes. |
| `evento_acceso` | MANTENER | Auditoría de autenticación sigue vigente. |
| `bitacora` | MODIFICAR | Sustituye columnas de tramo por proyecto/ProyectoNucleo y conserva antes/después. |
| `schema_migrations` | MANTENER | Control de historia desde `004`; `031` exigirá `030`. |
| `perfil_mapeo_importacion` | MODIFICAR | Se conserva en un único importador geoespacial. |
| `catalogo_alias_territorial` | MANTENER | Sigue siendo útil para resolver fuentes externas sin confundir IDs. |
| `importacion_archivo` | MODIFICAR | Será la cabecera única de staging para trazo, núcleo y parcela. |
| `importacion_feature` | MODIFICAR | Admitirá geometría genérica validada según el objetivo. |
| `carga_geoespacial` | ELIMINAR | Duplica `importacion_archivo`; sus capacidades útiles se consolidan allí. |
| `carga_geoespacial_feature` | ELIMINAR | Duplica `importacion_feature`. |
| `spatial_ref_sys` | MANTENER | Catálogo técnico administrado por PostGIS. |
| `geometry_columns` | MANTENER | Vista técnica administrada por PostGIS. |
| `geography_columns` | MANTENER | Vista técnica administrada por PostGIS. |

### 3.1 Vistas, funciones, triggers, constraints e índices

| Objeto o familia actual | Clasificación | Tratamiento |
|---|---|---|
| `vw_afectacion_ciclo_estado` | ELIMINAR | Depende completamente de ciclos y límites calculados. |
| `vw_afectacion_estado` | ELIMINAR | Su estado se basa en conclusión de ciclos. |
| `vw_tramo_nucleo_estado` | ELIMINAR | Se reemplaza por `vw_proyecto_nucleo_resumen`. |
| `vw_dashboard_liberacion` | ELIMINAR | Agrupa por tramo y mezcla geometría con avance administrativo. |
| `vw_orv_estado` | RECREAR | Sólo deriva vigencia a partir de fechas/estatus de ORV. |
| Funciones `fn_2b_*` | ELIMINAR | Creación/sincronización de ciclos, terminalidad, límites, pagos y secuencias. |
| Funciones de superficie de convenio/afectación | ELIMINAR | `fn_calcular_superficie_liberada_afectacion`, sincronización y bloqueos de reducción. |
| Funciones espaciales de negocio `fn_019_*`, `fn_026_*`, `fn_validar_coherencia_espacial` | ELIMINAR | Intersección y autoridad espacial ya no son reglas administrativas. |
| Funciones `fn_017_validar_*geometria*` | ELIMINAR | La ubicación de parcela/núcleo no bloqueará captura; quedan CHECK de validez. |
| `fn_015_validar_hijo_activo`, `fn_015_validar_baja_padre`, `fn_015_validar_geometria_padre` | ELIMINAR | Se retira la jerarquía tramo/franja y la baja se gobierna desde servicios transaccionales. |
| `fn_015_validar_administrador_activo` | MANTENER | Sigue protegiendo la existencia de al menos un administrador activo. |
| Funciones de expropiación/uso común/regresión de convenio | ELIMINAR | Implementan gates globales o una secuencia no aprobada. Las condiciones quedan como hechos. |
| Funciones de parcela/titular | RECREAR | La participación y pertenencia al núcleo se expresan con CHECK/FK y un único trigger de coherencia de afectación. |
| Funciones de suficiencia/protección de pago | ELIMINAR | Dependían del ciclo y de límites inferidos; los pagos son hechos y sus conciliaciones se reportan. |
| `fn_validar_documentacion_soporte_referencia` | RECREAR | Se generaliza para `documento_vinculo` y `trazabilidad_fuente`. |
| `fn_audit_log` | MODIFICAR | Debe resolver `id_proyecto`/`id_proyecto_nucleo` y redactar secretos como hoy. |
| Funciones `fn_008_*` | MANTENER | Integridad de autenticación y sesiones. |
| `fn_018_normalizar_nombre_nucleo` | MANTENER | Soporta unicidad activa del maestro de núcleos. |
| `fn_020_validar_alias_territorial` | MANTENER | Protege la resolución explícita de alias de importación. |
| Funciones y job de alertas ORV | ELIMINAR | La vigencia se deriva; no se persisten alertas en esta primera versión objetivo. |
| Triggers `trg_2b_*` | ELIMINAR | Implementan la máquina de estados/ciclos retirada. |
| Triggers `trg_019_*`, `trg_026_*`, `trg_validar_coherencia_espacial` | ELIMINAR | Implementan gates GIS retirados. |
| Triggers `trg_prevent_delete_*` | ELIMINAR | Se sustituyen por permisos: el rol de aplicación no tendrá `DELETE`; migraciones/seed sí. |
| Triggers `trg_baja_logica_*` | ELIMINAR | Se sustituyen por CHECK de coherencia y servicios explícitos de baja/reactivación. |
| Triggers `trg_audit_*` | RECREAR | Sólo sobre tablas objetivo que cambian hechos de negocio. |
| Índices por `id_tramo`, `id_tramo_nucleo`, `id_ciclo_afectacion` | ELIMINAR | Sus columnas desaparecen. |
| GiST de afectación, tramo, franja y sección | ELIMINAR | No existen esas geometrías objetivo. |
| GiST de núcleo y parcela | MANTENER | Apoyo cartográfico, nunca fuente oficial. |
| Constraints compuestas para repetir tramo/núcleo/ciclo en hijos | ELIMINAR | Se reemplazan por FK simples y validaciones de alcance puntuales. |

Los únicos triggers de integridad de dominio nuevos que se justifican son: coherencia parcela-ProyectoNucleo en afectación, coherencia ProyectoNucleo/ámbito en los vínculos de convenio y FIFONAFE, validación de la asamblea de autorización colectiva, obligaciones diferidas de vínculos requeridos y validación del vínculo documental/polimórfico. No se reintroduce una secuencia obligatoria de estados.

## 4. Comparación de estrategia

| Criterio | Opción A: migración conservadora | Opción B: reset controlado |
|---|---|---|
| Datos reales a preservar | Ninguno | Ninguno |
| Complejidad | Backfills de tramo/ciclo, puentes, estados temporales y conciliación | Recreación directa y seed pequeño |
| Riesgo de conservar contradicciones | Alto | Bajo |
| Duración y pruebas | Mayor; exige compatibilidad doble | Menor; contrato único |
| Trazabilidad histórica | Preserva IDs sin valor funcional | Preserva historia de migraciones, no IDs de prueba |
| Decisión | Descartada | **Elegida** |

### 4.1 Reset controlado

El reset no será un `DROP` manual improvisado. La implementación deberá:

1. detener backend y scheduler;
2. exigir `APP_ENV` de desarrollo/prueba, nombre de base permitido y una confirmación explícita como `ALLOW_DESTRUCTIVE_TEST_RESET=1`;
3. producir un respaldo restorable y un inventario previo, aunque los datos sean de prueba;
4. verificar que `030` está aplicada y tomar advisory lock;
5. aplicar las migraciones nuevas con `ON_ERROR_STOP=1` y transacciones;
6. limpiar registros funcionales, asignaciones, sesiones y auditoría de prueba en orden de dependencia;
7. conservar o recargar desde fixture los catálogos de 32 entidades y 2,478 municipios;
8. recrear el administrador mediante el flujo seguro existente, nunca con contraseña embebida en seed;
9. ejecutar el seed objetivo sólo sobre dominio vacío;
10. validar esquema, API, UI, dashboard, RBAC y restauración.

No habrá tabla puente entre `tramo_nucleo` y `proyecto_nucleo`, backfill de ciclos, compatibilidad de IDs ni dual-write.

## 5. Convenciones del esquema objetivo

### 5.1 Auditoría y baja lógica

Las tablas de negocio marcadas **BL** incluyen:

- `activo BOOLEAN NOT NULL DEFAULT TRUE`;
- `creado_en TIMESTAMPTZ NOT NULL DEFAULT now()`;
- `creado_por INTEGER NULL FK usuario`;
- `actualizado_en TIMESTAMPTZ NULL`;
- `actualizado_por INTEGER NULL FK usuario`;
- `fecha_baja TIMESTAMPTZ NULL`;
- `id_usuario_baja INTEGER NULL FK usuario`;
- `motivo_baja TEXT NULL`;
- `observaciones TEXT NULL`.

Un CHECK exige metadatos de baja cuando `activo = FALSE`. El rol SQL de la aplicación no tendrá privilegio `DELETE` sobre tablas de negocio. Catálogos, bitácora, eventos, sesiones, versiones y staging usan su propia política indicada abajo.

### 5.2 Tipos y geometría

- PK de catálogos y dominio: `INTEGER` identity, conservando compatibilidad con el stack actual.
- PK de bitácora, versiones y staging de alto volumen: `BIGINT` identity.
- Montos: `NUMERIC(18,2)` no negativos.
- Superficies administrativas: `NUMERIC(14,6)` no negativas.
- Geometrías operativas: SRID 4326, `ST_IsValid`, no vacías y tipo exacto.
- Las validaciones espaciales sólo validan forma/SRID. No usan intersección como gate ni calculan superficie oficial.

## 6. Esquema objetivo exacto

### 6.1 Territorio, proyecto y contexto

| Tabla | PK y FK | Columnas y nulabilidad | UNIQUE / CHECK / índices | BL |
|---|---|---|---|---|
| `entidad_federativa` | PK `id_entidad` | `clave_inegi CHAR(2) NN`, `nombre VARCHAR(100) NN`, `activo NN` | UNIQUE `clave_inegi`; conteo de fixture = 32 | No; catálogo controlado |
| `municipio` | PK `id_municipio`; FK `id_entidad` | `clave_inegi CHAR(5) NN`, `nombre VARCHAR(150) NN`, `activo NN` | UNIQUE `clave_inegi`; índice `(id_entidad,nombre)`; conteo = 2,478 | No; catálogo controlado |
| `proyecto` | PK `id_proyecto` | `clave_proyecto VARCHAR(30) NN`, `nombre_proyecto VARCHAR(200) NN`, `descripcion TEXT NULL`, `fecha_inicio DATE NULL`, `fecha_fin DATE NULL` | UNIQUE `clave_proyecto`; CHECK orden de fechas; índice nombre | Sí |
| `nucleo_agrario` | PK `id_nucleo`; FK `id_municipio` | `nombre_nucleo VARCHAR(300) NN`, `tipo_nucleo VARCHAR(20) NN`, `comunidad_indigena BOOLEAN NN DEFAULT FALSE`, `geometria_poligono MULTIPOLYGON NULL`, `fuente_geometria`, `fecha_fuente_geometria`, IDs externos/procedencia NULL | CHECK tipo `ejido/comunidad`; CHECK geometría; UNIQUE parcial por municipio/tipo/nombre normalizado; GiST geometría; índices municipio/tipo | Sí |
| `proyecto_nucleo` | PK `id_proyecto_nucleo`; FK `id_proyecto NN`, `id_nucleo NN` | `residencia VARCHAR(300) NULL`, `responsable_nombre VARCHAR(300) NULL`, `contacto VARCHAR(150) NULL` | UNIQUE parcial activo `(id_proyecto,id_nucleo)`; índices por proyecto y núcleo | Sí |
| `proyecto_nucleo_referencia` | PK `id_referencia`; FK `id_proyecto_nucleo NN` | `tipo_referencia VARCHAR(30) NN`, `valor VARCHAR(150) NN`, `es_principal BOOLEAN NN` | CHECK tipo `consecutivo/clave_tramo/numero_tramo/otro` y valor no vacío; UNIQUE parcial `(id_proyecto_nucleo,tipo_referencia,valor)`; máximo un principal activo por tipo; procedencia en `trazabilidad_fuente` | Sí |

**Decisión sobre consecutivos.** Existe un solo `proyecto_nucleo` activo por proyecto y núcleo. Los consecutivos son referencias de fuente, no expedientes distintos: se guardan como filas de `proyecto_nucleo_referencia`. La API expone `consecutivo_principal` como dato derivado de la referencia marcada principal. Esto soporta múltiples consecutivos sin duplicar ORV, padrón, actividades, afectaciones o dashboard y evita dos fuentes de verdad.

### 6.2 Personas, ORV, padrón y parcelas

| Tabla | PK y FK | Columnas y nulabilidad | UNIQUE / CHECK / índices | BL |
|---|---|---|---|---|
| `persona` | PK `id_persona` | `curp`, `rfc`, `nombre NN`, apellidos, teléfono, correo NULL; `datos_identidad_incompletos BOOLEAN NN`; `origen_registro VARCHAR(40) NN` | UNIQUE parcial CURP normalizada; índice de nombre normalizado | Sí |
| `orv` | PK `id_orv`; FK `id_nucleo` | `numero_orv`, `inicio_vigencia`, `fin_vigencia`, `estatus_fuente` NULL; `acta_eleccion_inscrita_ran BOOLEAN NULL`; `fecha_inscripcion_acta_ran DATE NULL` | CHECK orden de vigencia; UNIQUE parcial `(id_nucleo,inicio_vigencia)` cuando exista; índices núcleo/fin | Sí |
| `orv_integrante` | PK `id_orv_integrante`; FK `id_orv`, `id_persona` | `cargo VARCHAR(80) NN`, `fecha_inicio`, `fecha_fin` NULL | UNIQUE parcial `(id_orv,id_persona,cargo)`; CHECK fechas; índices ORV/persona | Sí |
| `padron_historial` | PK `id_padron`; FK `id_nucleo` | `fecha_padron DATE NULL`, `numero_ejidatarios_comuneros INTEGER NULL` | CHECK cantidad >= 0 y al menos fecha o cantidad; UNIQUE parcial `(id_nucleo,fecha_padron)`; índice núcleo/fecha desc | Sí |
| `parcela` | PK `id_parcela`; FK `id_nucleo` | `tipo_parcela VARCHAR(30) NN`, `no_parcela`, `no_parcela_ppt`, `certificado_parcelario`, `folio_derechos` NULL; `constancia_vigencia_fecha DATE NULL`; `geometria_poligono MULTIPOLYGON NULL`, `fuente_geometria`, `fecha_fuente_geometria` NULL | CHECK tipo `individual/copropiedad/otro/no_determinado`; UNIQUE parciales por núcleo para `no_parcela` y `no_parcela_ppt`; GiST geometría; índices certificado/folio | Sí |
| `parcela_titular` | PK `id_parcela_titular`; FK `id_parcela`, `id_persona` | `tipo_derecho VARCHAR(50) NN`, `porcentaje_participacion NUMERIC(7,4) NULL`, fechas NULL | CHECK 0 < porcentaje <= 100 y orden de fechas; UNIQUE parcial `(id_parcela,id_persona,tipo_derecho)`; índices parcela/persona | Sí |

`parcela.nombre_titular` desaparece. Toda titularidad vive en `parcela_titular`; el literal original de Excel se preserva en `trazabilidad_fuente`. La parcela puede existir sin geometría y la falta de geometría nunca bloquea afectación, convenio o pago.

### 6.3 Actividades y afectaciones

| Tabla | PK y FK | Columnas y nulabilidad | UNIQUE / CHECK / índices | BL |
|---|---|---|---|---|
| `actividad_campo` | PK `id_actividad`; FK `id_proyecto_nucleo NN` | `tipo_actividad VARCHAR(30) NN`, `contexto_actividad VARCHAR(40) NN`, `fecha_programada`, `fecha_realizada` NULL, `responsable VARCHAR(300) NULL`, `resultado TEXT NULL`, `observaciones TEXT NULL` | CHECK tipo `sensibilizacion/caminamiento`; contexto `general/superficie_adicional/obras_complementarias/otro`; CHECK fechas; índices PN/tipo/contexto/fechas | Sí |
| `afectacion` | PK `id_afectacion`; FK `id_proyecto_nucleo NN`; FK `id_parcela NULL` | `tipo_afectacion VARCHAR(20) NN`, `destino_superficie VARCHAR(100) NULL`, `no_parcela_solar VARCHAR(100) NULL`, `superficie_preliminar_ha`, `superficie_afectada_ha` NULL, `situacion VARCHAR(100) NULL`, `condicion_especial VARCHAR(50) NULL`, `descripcion_condicion TEXT NULL`, `avaluo_monto`, `avaluo_fecha`, `avaluo_referencia`, `avaluo_institucion` NULL | CHECK colectivo <=> parcela NULL; individual <=> parcela NN; superficies/avalúo >= 0; condición NULL o `expropiacion_directa/comunidad_indigena/no_afectacion_uso_comun/otro`; `otro` exige descripción; trigger mínimo verifica que parcela y PN pertenezcan al mismo núcleo; índices PN/tipo, parcela, destino, condición | Sí |

`afectacion` no contiene geometría. Expropiación directa y otras condiciones se registran en la afectación correspondiente y no cambian el estado global de `proyecto_nucleo`. `comunidad_indigena` sigue siendo un atributo del núcleo. Una condición colectiva no bloquea la ruta individual.

`actividad_campo` no agrega `id_afectacion`, `id_convenio` ni ciclo. Sensibilización y caminamiento son hechos del `proyecto_nucleo`; `contexto_actividad` distingue el bloque operativo sin convertirlo en propietario relacional. Si una evidencia pertenece específicamente a otro registro ya creado, se vincula mediante `documento_vinculo`.

### 6.4 Asamblea y RAN del acta

| Tabla | PK y FK | Columnas y nulabilidad | UNIQUE / CHECK / índices | BL |
|---|---|---|---|---|
| `asamblea` | PK `id_asamblea`; FK `id_proyecto_nucleo NN`; FK `id_padron NULL` | `tipo_asamblea VARCHAR(40) NN`, `proposito TEXT NULL`, `fecha_expedicion_primera`, `fecha_programada_primera`, `fecha_expedicion_segunda`, `fecha_programada_segunda`, `fecha_realizada` NULL; `resultado VARCHAR(50) NULL`; `fecha_ingreso_ran`, `numero_solicitud_ran`, `calificacion_registral_ran`, `fecha_inscripcion_ran` NULL; `observaciones TEXT NULL` | CHECK tipo `anuencia/modificatorio/superficie_adicional/obras_complementarias/retiro_fondos/otra`; CHECK fechas básicas; trigger verifica padrón del mismo núcleo; índices PN/tipo, fechas RAN, solicitud | Sí |

`asamblea` es exclusivamente de ámbito colectivo y no tiene `id_afectacion`: los marcadores Excel “PROGRAMADA POR NA” y “REALIZADA POR NA” identifican un solo hecho repetido en varias filas. La conciliación/importación debe resolver esas repeticiones a un mismo ID con trazabilidad de fuente; no se impone un UNIQUE inseguro basado sólo en tipo o fecha. El RAN del acta vive sólo en `asamblea`; no se reutilizan columnas de convenio ni un campo genérico de revisión. Uno o varios convenios colectivos pueden referir la misma asamblea mediante `convenio.id_asamblea_autorizacion`; ese FK es nullable y debe apuntar a una asamblea del mismo `proyecto_nucleo`.

### 6.5 Convenios y relación canónica

| Tabla | PK y FK | Columnas y nulabilidad | UNIQUE / CHECK / índices | BL |
|---|---|---|---|---|
| `convenio` | PK `id_convenio`; FK `id_proyecto_nucleo NN`; FK `id_convenio_padre NULL`; FK `id_asamblea_autorizacion NULL` | `ambito VARCHAR(20) NN`; `tipo_instrumento VARCHAR(20) NN DEFAULT 'convenio'`; `tipo_convenio VARCHAR(40) NULL`; `modalidad_especial`, `descripcion_modalidad`, `descripcion_instrumento` NULL; `consecutivo INTEGER NN DEFAULT 1`; `fecha_programada_firma`, `fecha_firma` NULL; `monto_90`, `monto_100`, `monto_bdt`, `superficie_ha` NULL; `fecha_programada_ingreso_ran`, `ingreso_ran_fecha`, `numero_solicitud_ingreso`, `calificacion_registral`, `fecha_inscripcion_ran` NULL | CHECK tipos por ámbito; modalidad NULL o `permuta/otra`, con descripción obligatoria para `otra`; instrumento `otro` exige descripción; montos/superficie >= 0 y `monto_90 <= monto_100`; padre distinto de sí; UNIQUE parcial `(id_convenio_padre,consecutivo)`; índices PN/ámbito/tipo, padre, fechas RAN | Sí |
| `convenio_afectacion` | PK `id_convenio_afectacion`; FK `id_convenio NN`, `id_afectacion NN` | `rol VARCHAR(20) NN DEFAULT principal` | UNIQUE parcial activo `(id_convenio,id_afectacion)`; máximo un rol principal activo por convenio; trigger exige mismo PN y mismo ámbito | Sí |

Reglas cerradas:

- `convenio` **no** tiene `id_afectacion`;
- toda asociación vive en `convenio_afectacion`;
- una transacción de creación inserta convenio + vínculo principal;
- un constraint trigger diferido impide confirmar un convenio activo sin al menos un vínculo activo;
- la captura normal parte de una afectación y crea automáticamente el vínculo principal;
- la acción excepcional “Asociar otra afectación” agrega un vínculo adicional;
- todas las afectaciones de un convenio deben pertenecer al mismo `proyecto_nucleo` y al mismo ámbito;
- el padre debe pertenecer al mismo `proyecto_nucleo` y ámbito;
- `id_asamblea_autorizacion`, cuando exista, debe pertenecer al mismo `proyecto_nucleo` y sólo se admite en convenios colectivos; una asamblea puede autorizar varios convenios;
- al crear un modificatorio, el servicio copia como punto de partida los vínculos activos del convenio padre; cualquier cambio posterior sigue las mismas validaciones;
- `tipo_convenio = cop_original` y `modalidad_especial = permuta` representa el caso ordinario de permuta;
- si el instrumento real no es un COP, se usa `tipo_instrumento = otro`, `tipo_convenio = NULL` y descripción obligatoria.

`convenio.superficie_ha` es la superficie propia del instrumento. No sustituye `afectacion.superficie_preliminar_ha` ni `afectacion.superficie_afectada_ha`.

### 6.6 FIFONAFE, indemnización y pago

| Tabla | PK y FK | Columnas y nulabilidad | UNIQUE / CHECK / índices | BL |
|---|---|---|---|---|
| `tramite_fifonafe` | PK `id_tramite_fifonafe`; FK `id_proyecto_nucleo NN` | `ambito VARCHAR(20) NN`, `estatus VARCHAR(30) NN`; `no_oficio_fifonafe_a_dgaopr`, `fecha_oficio_fifonafe_a_dgaopr`; `no_oficio_dgaopr_a_representacion`, `fecha_oficio_dgaopr_a_representacion`; `no_oficio_respuesta_representacion_a_dgaopr`, `fecha_oficio_respuesta_representacion_a_dgaopr`; `no_oficio_respuesta_dgaopr_a_fifonafe`, `fecha_oficio_respuesta_dgaopr_a_fifonafe`, todos NULL; `hay_conflictos BOOLEAN NULL`, `resultado_no_conflictos TEXT NULL`, `observaciones TEXT NULL` | CHECK ámbito `colectivo/individual`; CHECK estatus `programado/pendiente/completo/cancelado/otro`; índices PN/ámbito/estatus/fechas | Sí |
| `tramite_fifonafe_afectacion` | PK `id_tramite_fifonafe_afectacion`; FK `id_tramite_fifonafe NN`, `id_afectacion NN` | Sin datos de negocio adicionales | UNIQUE `(id_tramite_fifonafe,id_afectacion)`; trigger exige mismo PN y mismo ámbito; índices trámite/afectación | Sí |
| `indemnizacion` | PK `id_indemnizacion`; FK `id_afectacion NN` | `estatus VARCHAR(30) NN`, `descripcion_estatus TEXT NULL`, `fecha_programada`, `fecha_resolucion` NULL | UNIQUE parcial una indemnización activa por afectación; CHECK estatus `pendiente/programado/completo/otro`; `otro` exige descripción; CHECK fechas; índices afectación/estatus | Sí |
| `pago` | PK `id_pago`; FK `id_indemnizacion NN`; FK `id_persona_beneficiaria NULL` | `fecha_pago DATE NN`, `monto NUMERIC(18,2) NN`, `beneficiario_nombre VARCHAR(300) NN`, `referencia VARCHAR(150) NULL`, `medio_pago VARCHAR(30) NULL`, `observaciones TEXT NULL` | CHECK monto > 0; CHECK medio permitido u `otro`; UNIQUE parcial `(id_indemnizacion,referencia)`; índices indemnización/fecha y persona | Sí |

Las cadenas canónicas son independientes:

```text
Pago -> Indemnizacion -> Afectacion -> ProyectoNucleo

TramiteFifonafe -> TramiteFifonafeAfectacion
                -> Afectacion -> ProyectoNucleo
```

`tramite_fifonafe` no tiene FK a convenio ni a ciclo. Un trámite debe cubrir al menos una afectación activa y puede cubrir varias sin duplicar los cuatro oficios; el vínculo valida `proyecto_nucleo` y ámbito. La conciliación de filas repetidas reutiliza el trámite identificado y conserva trazabilidad, en vez de insertar una copia por afectación. `indemnizacion` no depende obligatoriamente de FIFONAFE y admite como máximo un registro activo por afectación. `pago` depende sólo de indemnización, lo que permite hechos directos o bancarios cuando correspondan.

### 6.7 Documentos y trazabilidad de fuente

| Tabla | PK y FK | Columnas y nulabilidad | UNIQUE / CHECK / índices | BL |
|---|---|---|---|---|
| `documento` | PK `id_documento` | `tipo_documento VARCHAR(80) NN`, `estado VARCHAR(20) NN`, `titulo VARCHAR(250) NULL`, `descripcion TEXT NULL` | CHECK estado `disponible/faltante/referenciado`; índice tipo/estado | Sí |
| `documento_version` | PK `id_documento_version`; FK `id_documento NN`, `id_usuario_carga NN` | `numero_version INTEGER NN`, `hash_sha256 CHAR(64) NN`, `tamano_bytes BIGINT NN`, `nombre_original VARCHAR(255) NN`, `ruta_almacenamiento TEXT NN`, `tipo_mime VARCHAR(150) NULL`, `fecha_carga NN` | UNIQUE `(id_documento,numero_version)`, `ruta_almacenamiento` y hash/documento; CHECK versión/tamaño; inmutable | No; append-only |
| `documento_vinculo` | PK `id_documento_vinculo`; FK `id_documento NN` | `entidad_tipo VARCHAR(50) NN`, `entidad_id INTEGER NN` | UNIQUE parcial vínculo activo; trigger valida objetivo permitido/existente; índice `(entidad_tipo,entidad_id)` | Sí |
| `trazabilidad_fuente` | PK `id_trazabilidad BIGINT`; `id_usuario_registro NULL` | `entidad_tipo`, `entidad_id`, `archivo`, `hoja`, `fila`, `columna`, `valor_original`, `tratamiento` NN/NULL según dato; `registrado_en NN` | CHECK tratamiento `PERSISTIR/DERIVAR/REFERENCIA/DOCUMENTAR/REVISAR/NO IMPLEMENTAR`; índice objetivo y `(archivo,hoja,fila)`; trigger valida objetivo | No; append-only |

Tipos documentales/vínculos permitidos incluyen `proyecto_nucleo`, `nucleo_agrario`, `orv`, `padron_historial`, `parcela`, `afectacion`, `asamblea`, `convenio`, `tramite_fifonafe`, `indemnizacion` y `pago`. El archivo Excel no se copia: sólo se conserva nombre, hoja, fila, columna y valor relevante.

### 6.8 Seguridad y auditoría

| Tabla | PK y FK | Columnas y nulabilidad | UNIQUE / CHECK / índices | BL |
|---|---|---|---|---|
| `usuario` | Actual | Nombre, correo, hash, rol y estado actuales | Rol `admin/operador/visualizador/geografo`; correo normalizado único | Sí |
| `usuario_proyecto` | PK `id_usuario_proyecto`; FK `id_usuario NN`, `id_proyecto NN`, `asignado_por NN -> usuario` | `fecha_asignacion NN` | UNIQUE parcial activo `(id_usuario,id_proyecto)`; índices usuario/proyecto | Sí |
| `estado_autenticacion_usuario` | Actual | Intentos, bloqueo, último acceso | Constraints actuales | No; estado técnico |
| `sesion_usuario` | Actual | Hashes, expiración, revocación, IP/UA | Constraints/índices actuales | No; revocable |
| `evento_acceso` | Actual | Evento, actor, sesión, motivo, IP/UA | Append-only e índices actuales | No |
| `bitacora` | PK `id_bitacora BIGINT`; FK usuario/proyecto/PN/núcleo NULL | `entidad_tipo`, `entidad_id`, `accion`, `valor_anterior`, `valor_nuevo`, fecha, IP/UA | Índices fecha, usuario, proyecto/PN y objetivo | No; append-only |

Política de alcance:

- `admin` conserva acceso global;
- los demás roles sólo ven proyectos con `usuario_proyecto.activo = TRUE`;
- `operador` captura hechos del proyecto asignado;
- `visualizador` sólo consulta;
- `geografo` administra importación y geometrías de trazo/núcleo/parcela dentro de proyectos asignados, sin cambiar hechos financieros;
- las consultas filtran por proyecto antes de paginar;
- ORV, padrón, núcleo y parcela son maestros compartidos: se accede a ellos si existe al menos un `proyecto_nucleo` del proyecto autorizado; sólo admin/geógrafo cambia geometría del maestro;
- el contexto de seguridad se resuelve por relaciones canónicas: convenio por `convenio_afectacion`, FIFONAFE por `id_proyecto_nucleo` y sus vínculos, e indemnización/pago por la afectación; no por IDs redundantes enviados por el cliente.

### 6.9 Trazo e importación geoespacial

| Tabla | PK y FK | Columnas y nulabilidad | UNIQUE / CHECK / índices | BL |
|---|---|---|---|---|
| `trazo_proyecto` | PK `id_trazo`; FK `id_proyecto NN` | `version INTEGER NN`, `geometria_linea MULTILINESTRING NN`, `fuente VARCHAR(250) NN`, `fecha_fuente DATE NULL`, `fecha_vigencia_inicio DATE NN`, `fecha_vigencia_fin DATE NULL` | UNIQUE `(id_proyecto,version)`; máximo uno activo; CHECK geometría/fechas/fuente; GiST geometría | Sí |
| `perfil_mapeo_importacion` | Actual/modificado | Mapeo JSONB, objetivo, opciones, usuario | Objetivos `trazo_proyecto/nucleo_agrario/parcela`; nombre único | Sí técnico |
| `catalogo_alias_territorial` | Actual | Alias -> municipio, fuente/vigencia | Unicidad activa actual | Sí técnico |
| `importacion_archivo` | PK `id_importacion BIGINT` | Metadata, hash, CRS, mapeo, objetivo, estado, contadores, procedencia y usuarios | Objetivos permitidos; unicidad hash/objetivo; índices estado/usuario | Sí técnico |
| `importacion_feature` | PK `id_importacion_feature BIGINT`; FK archivo y resoluciones | `geometria_normalizada GEOMETRY NULL`, tipo, atributos, errores/advertencias, transformaciones, registro operativo NULL | Tipo geométrico según objetivo; UNIQUE archivo/índice; GiST geometría; índices estado/resolución | No; staging con retención |

Se elige `trazo_proyecto`, no una simplificación nominal de `franja_derecho_via`, porque elimina semántica residual de ancho, polígono de derecho de vía y tramo. Los cálculos de área/longitud del staging sirven únicamente para control de conversión; no alimentan superficies administrativas ni KPI.

## 7. Contratos de backend y frontend a reemplazar

### 7.1 Backend

- Crear modelos SQLAlchemy para las tablas objetivo y retirar clases legacy.
- Sustituir schemas que aceptan `id_tramo_nucleo` o `id_ciclo_afectacion` por `id_proyecto_nucleo`, `id_afectacion` o relaciones anidadas apropiadas.
- Dividir los endpoints monolíticos de `main.py` en routers de proyecto-núcleo, afectaciones, convenios, FIFONAFE, indemnizaciones, pagos y dashboard.
- Reemplazar `require_tramo_access`, `require_tramo_nucleo_access` y filtros por tramo con `require_project_access` y resolución de alcance por FK.
- Eliminar endpoints de ciclos, salida terminal global, candidatos, secciones y asignaciones por tramo.
- La creación de convenio recibe una afectación inicial y crea convenio + vínculo principal en una sola transacción.
- FIFONAFE recibe `id_proyecto_nucleo`, ámbito y afectaciones cubiertas; indemnización recibe su afectación y pago su indemnización. Ningún contrato acepta FK a ciclo ni usa FIFONAFE como padre obligatorio del pago.
- Consolidar los dos importadores en el flujo `importacion_archivo/importacion_feature`.

### 7.2 Frontend

- `ExpedientesList` pasa a navegación Proyecto -> Entidad -> Municipio -> Núcleo.
- `ExpedienteDetail` se reemplaza por espacio de trabajo de `ProyectoNucleo` con pestañas aprobadas.
- `AfectacionSubexpediente` elimina ciclos y presenta hechos directos.
- `FormConvenio` inicia desde una afectación y ofrece asociación adicional como acción secundaria.
- `Dashboard` deja tarjetas por tramo y consume KPI por proyecto/periodo.
- `Mapa` filtra por proyecto y muestra trazo, núcleo y parcelas opcionales.
- `AdministracionTerritorial` elimina tramo/sección/candidato y administra ProyectoNucleo, trazo y `usuario_proyecto`.
- Se retiran paneles de minutas/acuerdos/alertas si no tienen otra dependencia aprobada.

## 8. Dashboard objetivo

Se crearán dos vistas de lectura, sin materializar totales editables:

1. `vw_proyecto_nucleo_resumen`: datos de navegación y conteos por contexto.
2. `vw_dashboard_kpi`: formato largo por `id_proyecto`, año/periodo, indicador, `programado`, `realizado`, cantidad y superficie capturada cuando aplique.

Cada indicador usa un agregado independiente antes de unirse por proyecto para evitar multiplicación de filas N:M.

| KPI | Fuente objetiva |
|---|---|
| Núcleos | `COUNT(proyecto_nucleo)` activo |
| Sensibilizaciones / caminamientos | `actividad_campo.tipo_actividad`, fechas programada/realizada |
| Asambleas | `asamblea` agregada directamente por `id_proyecto_nucleo`, fechas programadas/realizada |
| RAN del acta | ingreso e inscripción en `asamblea` |
| COP colectivos/individuales | `convenio.ambito`, `tipo_convenio`, `fecha_firma` |
| Modificatorios | `convenio.tipo_convenio = modificatorio` |
| Superficie adicional / obras complementarias | tipo y `superficie_ha` de convenio |
| Ampliaciones / remanentes | tipo y `superficie_ha` de convenio |
| RAN del convenio | ingreso e inscripción en `convenio` |
| Retiro de fondos | `asamblea.tipo_asamblea = retiro_fondos` |
| Expropiación directa | `afectacion.condicion_especial` |
| Parcelas afectadas | `COUNT(DISTINCT afectacion.id_parcela)` individual |
| FIFONAFE / no conflictos | `tramite_fifonafe` agregado por trámite, sin contar sus vínculos N:M |
| Indemnizaciones | `indemnizacion` agregada por su `afectacion` |
| Pagos | `pago` agregado por `indemnizacion`, cantidad y suma de monto |
| Superficies | suma separada de preliminar, afectada y propia de convenio |

Cada familia se agrega de forma independiente antes de cualquier join N:M; cuando un filtro requiera atravesar vínculos se cuenta el ID distinto del hecho. Ninguna definición usa `ST_Area`, presencia de geometría ni intersección. Los números del Excel general son contrato de aceptación; no se insertan como filas de totales.

## 9. Migraciones propuestas

### 031 — `031_reset_dominio_proyecto_nucleo.sql`

- Preflight: versión `030`, entorno/confirmación destructiva, advisory lock y respaldo verificado.
- Retirar vistas y triggers que dependen de ciclo/tramo antes de tocar tablas.
- Eliminar primero candidatos, minutas/acuerdos, alertas y todas las tablas funcionales dependientes; retirar después `tramo_nucleo`, `afectacion_ciclo` y las tablas de hechos incompatibles.
- Crear/recrear ProyectoNucleo, referencias, ORV/padrón/personas/parcelas, actividad, afectación, asamblea, convenio/vínculos, FIFONAFE y su vínculo N:M, indemnización, pago, documentos y trazabilidad.
- Modificar bitácora y crear `usuario_proyecto`.
- Conservar tablas técnicas de autenticación y catálogos.
- Registrar `031` sólo al final.

### 032 — `032_cleanup_legacy_gis_importacion.sql`

- Crear `trazo_proyecto` y adaptar el importador canónico.
- Consolidar capacidades de staging necesarias.
- Eliminar el remanente técnico `tramo`, `franja_derecho_via`, `seccion_derecho_via`, `usuario_tramo`, `carga_geoespacial*` y sus objetos SQL dependientes. `tramo_nucleo`, ciclos y hechos funcionales incompatibles ya habrán desaparecido en `031`.
- Eliminar funciones/índices/constraints espaciales y de ciclo obsoletos.
- Registrar `032` sólo al final.

### 033 — `033_dashboard_modelo_objetivo.sql`

- Crear `vw_orv_estado`, `vw_proyecto_nucleo_resumen` y `vw_dashboard_kpi`.
- Conceder sólo lectura al rol de aplicación.
- Incluir consultas de conciliación de KPI del seed y ausencia de `ST_Area`.
- Registrar `033` sólo al final.

Tres migraciones separan dominio, contracción técnica y lectura analítica sin introducir expand/migrate/switch ni dual-write. Deben probarse tanto sobre una copia en versión `030` como desde instalación limpia siguiendo la historia vigente.

## 10. Seed objetivo

El seed se divide en dos artefactos de implementación:

1. **Catálogo territorial idempotente:** fixture versionado y con checksum para 32 entidades y 2,478 municipios, con UPSERT por clave INEGI.
2. **Dominio demo recreable:** script transaccional que exige dominio vacío, usa claves naturales conocidas y aborta ante un estado parcial. No contiene contraseñas.

Datos propuestos:

- proyectos `MÉXICO-QUERÉTARO` y `QUERÉTARO-IRAPUATO`; el segundo demuestra estado vacío sin inventar totales;
- 4 o 5 núcleos, usando de los Excel `SAN ILDEFONSO`, `AHORCADO`, `AGUA AZUL` y `PUEBLO NUEVO DE JASSO`; se agrega una comunidad marcada explícitamente como caso sintético de QA porque los renglones detallados inspeccionados no aportan una comunidad;
- ORV, integrantes y padrón;
- sensibilización y caminamiento generales y una actividad contextual;
- afectaciones colectivas con tierras de uso común, parcela escolar y solar/otro destino;
- parcelas individuales `P-172`, `P-170`, `P-173` y `P-169` de Ahorcado, con titulares normalizados a partir del Excel;
- una parcela con geometría sintética válida y las demás sin geometría;
- afectaciones individuales para las parcelas;
- COP colectivo, COP individual, modificatorio, superficie adicional, ampliación y ampliación remanente;
- una asamblea colectiva del ProyectoNucleo con RAN del acta, referida por varios convenios que en conjunto autorizan más de una afectación;
- un trámite FIFONAFE colectivo con los cuatro oficios que cubre varias afectaciones;
- un trámite FIFONAFE individual compartido por afectaciones de varias parcelas, sin repetir los oficios;
- una afectación con indemnización y pago directo/bancario sin FK obligatoria a FIFONAFE;
- `PUEBLO NUEVO DE JASSO` con `cop_original + modalidad_especial=permuta`, preservando la observación fuente;
- un convenio con vínculo principal y vínculo adicional a dos afectaciones, inspirado en el caso “1 COP PARA DOS SOLARES, DUDA” pero identificado como escenario de prueba de cardinalidad;
- documentos disponibles/faltantes, versiones pequeñas de fixture, observaciones y `trazabilidad_fuente` sin copiar los Excel.

Los totales esperados del seed se declaran en tests, no en tablas. El script fija fechas y valores; no usa `date.today()`, IDs heredados ni geometría para generar hechos administrativos.

## 11. Pruebas requeridas

### 11.1 Migración y esquema

- aplicar `031`-`033` sobre copia de `030` con datos de prueba;
- comprobar rollback total ante fallo inducido;
- comprobar que el guard impide ejecución fuera de entorno permitido;
- instalar desde base limpia y verificar `schema_migrations`;
- afirmar presencia de tablas/constraints/índices objetivo y ausencia de objetos legacy;
- verificar 32 entidades y 2,478 municipios, claves únicas y checksum del fixture;
- verificar que no existe `id_tramo`, `id_tramo_nucleo`, `id_ciclo_afectacion`, `ST_Area` en vistas de negocio ni triggers con `ST_Intersects`.

### 11.2 Dominio y API

- alta única de ProyectoNucleo y múltiples referencias/consecutivos;
- colectivo sin parcela e individual con parcela obligatoria del mismo núcleo;
- parcela con/sin geometría y seguimiento completo en ambos casos;
- actividad general y contextual perteneciente a ProyectoNucleo, sin afectación ni ciclo;
- asamblea colectiva compartida por varios convenios/afectaciones y rechazo de su uso desde convenio individual;
- RAN del acta independiente de RAN del convenio;
- tipos de convenio por ámbito, padre/consecutivo y permuta como modalidad;
- creación transaccional de vínculo principal y asociación multiafectación;
- rechazo de afectaciones cruzadas entre ProyectoNucleo o ámbitos;
- FIFONAFE con captura progresiva de cuatro oficios y asociación N:M a afectaciones del mismo ProyectoNucleo/ámbito;
- un mismo FIFONAFE individual cubriendo afectaciones de varias parcelas sin duplicar el trámite;
- indemnización única activa por afectación, separada de FIFONAFE, con múltiples pagos y beneficiario/evidencia;
- baja lógica y bitácora con contexto de proyecto.

### 11.3 Seguridad

- admin global;
- operador/visualizador/geógrafo con proyectos asignados y no asignados;
- filtros aplicados antes de paginación/exportación/dashboard;
- acceso documental resuelto por el recurso padre;
- sesión, bloqueo, CSRF, revocación y redacción de secretos sin regresión;
- el rol SQL de aplicación no puede ejecutar `DELETE` físico.

### 11.4 Dashboard y frontend

- conteos exactos del seed para cada KPI y periodo;
- no duplicación por `convenio_afectacion` ni `tramite_fifonafe_afectacion` N:M, y conteo único de asambleas compartidas;
- superficies iguales a valores capturados aunque cambie la geometría;
- ProyectoNucleo visible sin trazo y parcela visible sin geometría;
- navegación desktop/mobile Proyecto -> Entidad -> Municipio -> Núcleo;
- rutas colectiva e individual completas, asociación excepcional de afectación y estados vacíos;
- administración por proyecto, mapa y permisos E2E;
- pruebas sin depender de IDs de datos actuales.

## 12. Secuencia de implementación

1. Preparar fixture territorial, migraciones y pruebas de contrato SQL.
2. Aplicar `031` en base aislada y actualizar modelos/schemas/servicios/routers para el contrato nuevo.
3. Actualizar frontend y E2E.
4. Aplicar `032` y demostrar que ninguna referencia legacy queda en código o SQL.
5. Aplicar `033` y reconstruir dashboard/reportes.
6. Detener servicios y respaldar la base de desarrollo.
7. Recrear la base desde estado limpio y aplicar historia completa.
8. Crear administrador seguro, cargar catálogo y ejecutar seed demo.
9. Ejecutar pruebas SQL, backend, frontend, seguridad, GIS y dashboard.
10. Actualizar `Arquitectura_Actual.md` y `Diccionario_Datos_SSALFER.md` sólo cuando la implementación sea real.

## 13. Riesgos y mitigaciones

| Riesgo | Nivel | Mitigación / gate |
|---|---|---|
| Ejecutar reset destructivo en una base incorrecta | Crítico | Triple guard entorno + nombre + confirmación, backup y advisory lock. |
| Catálogo completo no reproducible desde Git | Alto | Crear fixture versionado, fuente/checksum y test exacto 32/2,478 antes del seed. |
| Gran superficie de referencias legacy | Alto | Búsqueda estática como gate y actualización por capas; no mantener aliases temporales. |
| Duplicación de filas del dashboard por relaciones N:M o asambleas compartidas | Alto | Agregados independientes y pruebas exactas con convenios y trámites multiafectación. |
| Vínculo convenio-afectación inconsistente | Alto | Relación única, trigger diferido, mismo PN/ámbito y transacción atómica. |
| Duplicar asambleas u oficios repetidos por fila Excel | Alto | Conciliación por hecho, trazabilidad de fuente y pruebas de importación que reutilicen Asamblea/FIFONAFE. |
| Vínculo FIFONAFE-afectación fuera de alcance | Alto | UNIQUE del par, trigger de mismo ProyectoNucleo/ámbito y pruebas de rechazo cruzado. |
| Ruptura del importador geoespacial útil | Medio | Consolidar sobre el importador con staging/perfiles/alias y portar sus pruebas de seguridad. |
| Datos Excel incompletos o fechas seriales | Medio | Campos NULL, normalización explícita y trazabilidad del literal; no convertir desconocido en falso/cero. |
| Documentos polimórficos sin FK declarativa | Medio | Lista cerrada de tipos, trigger de existencia, servicio de alcance y pruebas por tipo. |
| Reintroducir GIS como regla de negocio | Medio | Tests de definición de vistas/triggers y revisión que prohíba `ST_Area`/gates de intersección. |
| Baseline actual requiere aplicación manual ordenada | Medio | Mantener guía `001` + `004`-`033`; preparar squash sólo después de estabilizar. |

## 14. Gates para implementar

La implementación sólo se aprueba para merge/despliegue cuando se cumpla todo lo siguiente:

- [ ] Fixture territorial versionado con 32 entidades y 2,478 municipios, checksum y procedencia.
- [ ] Respaldo/restauración probados y guard destructivo validado.
- [ ] Migraciones `031`-`033` aplican sobre copia de `030` y sobre instalación limpia.
- [ ] Inventario final no contiene tablas, FK, funciones, triggers, vistas o índices legacy.
- [ ] Backend no contiene `id_tramo_nucleo` ni `id_ciclo_afectacion` en contratos objetivo.
- [ ] Frontend no navega por tramo ni muestra ciclos.
- [ ] `convenio_afectacion` es la única relación convenio-afectación y soporta N:M.
- [ ] Asamblea pertenece a ProyectoNucleo, es colectiva y puede autorizar varios convenios.
- [ ] `tramite_fifonafe_afectacion` cubre N:M sin FK obligatoria de FIFONAFE a convenio.
- [ ] Pago -> indemnización -> afectación -> ProyectoNucleo es la cadena financiera canónica; FIFONAFE no es su padre obligatorio.
- [ ] Geometría opcional no bloquea capturas y no alimenta KPI oficiales.
- [ ] RBAC por `usuario_proyecto` cubre lecturas, escrituras, documentos, exportaciones y dashboard.
- [ ] Seed demo es recreable y sus KPI esperados pasan.
- [ ] Suites SQL, pytest y Playwright pasan sin IDs heredados.
- [ ] Se actualizan documentos de arquitectura vigente después de implementar.

## 15. Baseline futura

Después de estabilizar `031`-`033` en al menos una recreación limpia y una actualización desde `030`, se recomienda una tarea separada para consolidar `001`-`033` en una baseline de instalación. La cadena histórica debe archivarse y conservarse para auditoría. Ese squash no forma parte de este diseño ni debe ocurrir antes de validar el refactor.

## 16. Gate final de diseño

**APROBADO PARA IMPLEMENTAR REESTRUCTURACIÓN**

El esquema objetivo, las cardinalidades, el alcance del reset, la eliminación legacy, el seed, los KPI, seguridad y desacoplamiento GIS están definidos. Los checks de la sección 14 son gates de ejecución verificables, no decisiones funcionales pendientes.
