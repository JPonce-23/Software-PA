# Evaluacion tecnica - Subcorte 2C: navegacion por afectacion y aislamiento documental

**Fecha:** 2026-08-04

**Propuesta evaluada:** `docs/propuestas/2026-08-04-subcorte-2c-navegacion-afectacion-aislamiento-documental-propuesta.md`

**Estado:** implementacion completa y validada tecnicamente en este entorno local.

## Antes de implementar

## 1. Trabajo vigente identificado

El trabajo vigente documentado en `ESTADO_PROYECTO.md` fue el **Subcorte 2C del
Corte principal 2: navegacion por afectacion y aislamiento documental**.

Al iniciar esta etapa, `ESTADO_PROYECTO.md` ya habia sido actualizado por el
usuario para registrar que la aceptacion funcional de 2B estaba completada y que
el siguiente paso tecnico era implementar 2C con base en la propuesta evaluada.

Alcance exacto:

1. Mantener `tramo_nucleo` como expediente maestro territorial.
2. Abrir cada `afectacion` como subexpediente operativo dentro de su
   `tramo_nucleo`.
3. Mostrar antecedentes compartidos sin moverlos ni duplicarlos.
4. Aislar actuaciones, pagos, minutas y documentos propios por afectacion.
5. Corregir el tipo documental invalido usado por el panel maestro.
6. Preservar autorizacion por rol y pertenencia territorial.

## 2. Resumen de la propuesta evaluada

La propuesta planteaba una implementacion incremental, expansiva y compatible:

- migracion 007 para admitir documentos de `tramo_nucleo` y minutas propias de
  afectacion/ciclo;
- ORM y contratos Pydantic alineados con el nuevo alcance documental;
- resolutores de autorizacion para relaciones documentales dinamicas;
- filtros backend por `id_afectacion` e `id_ciclo_afectacion`;
- endpoint agregado de subexpediente;
- ruta React `/expedientes/:id_tramo_nucleo/afectaciones/:id_afectacion`;
- parametrizacion de paneles de documentos, pagos, minutas y flujo;
- pruebas de aislamiento entre dos afectaciones del mismo expediente maestro.

La propuesta fue aceptada con ajustes: `tramo_nucleo` documental y minutas
propias dejaron de tratarse como decisiones abiertas y se clasificaron como
cambios tecnicos necesarios para cumplir 2C sin inferencias ambiguas.

## 3. Hallazgos de auditoria

1. La propuesta atiende el alcance vigente de `ESTADO_PROYECTO.md` y no reabre
   2A, 2B, seguridad formal ni derecho de via versionado.
2. La base local de esta maquina tenia inicialmente `schema_migrations` 004,
   005 y 006, pero cero datos operativos. La fotografia de 6/20 afectaciones
   correspondia a otra base de referencia y no era verificable aqui.
3. El esquema pre-007 rechazaba
   `documentacion_soporte.entidad_relacionada_tipo = 'tramo_nucleo'`, mientras
   el frontend ya lo necesitaba para documentos maestros.
4. `documentacion_soporte` validaba referencias en PostgreSQL, pero faltaba
   autorizacion territorial consistente para listado, versiones, descarga,
   carga y baja logica.
5. `minuta` solo tenia `id_tramo_nucleo` e `id_actividad`; asociar minutas
   propias por asunto, fecha o actividad habria violado la regla de no inferir
   relaciones ambiguas.
6. Asambleas, convenios, FIFONAFE y pagos tenian datos suficientes para aislar
   por afectacion/ciclo, pero faltaban filtros y validaciones de pertenencia.
7. No existia ruta frontend de subexpediente; la vista maestra era el unico
   punto de entrada operativo.
8. El script `npm run lint` dentro de la imagen temporal escaneo `node_modules`
   y reporto errores de terceros. La validacion aplicable del codigo propio fue
   `npx oxlint src`, que finalizo sin errores ni advertencias.

## 4. Matriz de evaluacion

| Area | Resultado | Evidencia | Ajuste requerido |
| --- | --- | --- | --- |
| Alcance funcional 2C | Aprobada | Coincide con `ESTADO_PROYECTO.md`: subexpediente por afectacion, antecedentes compartidos y aislamiento. | No ampliar a Corte 5 ni autenticacion formal. |
| Documento maestro `tramo_nucleo` | Aprobada con ajustes | DB pre-007 lo rechazaba y el panel maestro lo necesitaba. | Incluirlo en check/trigger PostgreSQL y Pydantic. |
| Minutas propias | Aprobada con ajustes | `minuta` no tenia relacion explicita con afectacion/ciclo. | Agregar columnas nullable con CHECK, FK compuesta y validacion de actividad/ciclo. |
| Modelo de datos | Aprobada | 006 ya aportaba `afectacion_ciclo` y relaciones de etapa. | Mantener migracion expansiva; no reclasificar historicos. |
| Contratos | Aprobada con ajustes | Tipos documentales eran `str`; minutas no exponian afectacion/ciclo. | Usar catalogo explicito y campos opcionales compatibles. |
| Servicios | Aprobada | Las reglas requieren transaccion unica y errores de dominio estables. | Validar pertenencia antes de escritura y conservar `set_audit_context`. |
| Endpoints | Aprobada | Faltaban filtros por afectacion/ciclo y agregado de subexpediente. | Agregar filtros con validacion de tramo/afectacion/ciclo. |
| Autorizacion | Aprobada con ajustes | Helpers territoriales existian, pero no cubrian relaciones documentales dinamicas. | Resolver acceso segun tipo/ID de entidad y aplicar a lecturas/escrituras. |
| Frontend | Aprobada | No existia pagina de subexpediente ni paneles parametrizados. | Agregar ruta y reutilizar paneles con alcance por entidad. |
| Pruebas | Aprobada | Faltaban regresiones 2C. | Agregar pruebas API/DB de aislamiento, documentos y permisos. |
| Datos existentes | Pendiente de validacion por ambiente | La base local no contiene datos operativos; otros equipos pueden diferir. | Preflight y respaldo por ambiente antes de ejecutar 007. |

## 5. Resultado de los gates

| Gate | Resultado | Justificacion |
| --- | --- | --- |
| Funcional | Superado | `ESTADO_PROYECTO.md` ya registra aceptacion 2B y 2C como siguiente implementacion tecnica. |
| Datos | Superado | 007 es expansiva, no destructiva, no infiere relaciones y protege reglas en PostgreSQL. |
| Seguridad | Superado | Se agrego resolucion territorial para documentos y minutas, y se conservaron roles existentes. |
| Arquitectura | Superado | Se mantiene `tramo_nucleo` maestro y `afectacion` subexpediente sin duplicar antecedentes. |
| Migracion | Superado | Requiere 006, usa transaccion, prevalidacion, advisory lock, CHECK/FK/trigger e insercion en `schema_migrations`. |
| Pruebas | Superado | Hay pruebas nuevas de aislamiento, permisos y documentos, mas suite backend completa y validacion frontend. |

## 6. Propuesta corregida

La propuesta corregida quedo asi:

1. `tramo_nucleo` es un tipo documental valido para documentos maestros.
2. Los documentos propios del subexpediente usan `entidad_relacionada_tipo =
   'afectacion'` y `entidad_relacionada_id = id_afectacion`.
3. Las minutas existentes permanecen compartidas; las minutas nuevas pueden
   pertenecer explicitamente a una afectacion/ciclo.
4. No se migran relaciones historicas por inferencia.
5. Las lecturas documentales no globales requieren entidad completa
   `entidad_tipo` + `entidad_id`; usuarios no administradores no pueden listar
   documentos sin alcance.
6. 2C no redefine la matriz de roles; solo cierra territorio/IDOR y mantiene la
   compatibilidad actual.
7. La interfaz conserva el expediente maestro y agrega un subexpediente por
   afectacion.

## 7. Decision de viabilidad

**Decision:** propuesta viable. Se inicio e implemento porque supero los gates
obligatorios despues de corregir los puntos anteriores.

## 8. Plan final de implementacion

1. Registrar estado Git inicial y respetar cambios existentes del usuario.
2. Agregar pruebas 2C de aislamiento, documentos y permisos.
3. Crear migracion 007 expansiva.
4. Actualizar ORM y contratos.
5. Implementar autorizacion documental/minutas y filtros por afectacion/ciclo.
6. Agregar endpoint agregado de subexpediente.
7. Parametrizar paneles React y agregar ruta de subexpediente.
8. Aplicar migracion local con respaldo previo.
9. Ejecutar suite backend completa y validaciones frontend.
10. Actualizar `ESTADO_PROYECTO.md` con resultados reales.

## Despues de implementar

## 9. Cambios realizados

| Archivo | Cambio | Justificacion |
| --- | --- | --- |
| `backend/db/migrations/007_subcorte_2c_navegacion_documental.sql` | Nueva migracion expansiva para documentos `tramo_nucleo`, columnas de minuta por afectacion/ciclo, FK, CHECK, trigger e indices. | Proteger integridad 2C tambien en PostgreSQL. |
| `backend/app/models.py` | Columnas y restricciones ORM de `Minuta`. | Reflejar el esquema ejecutable sin inferir relaciones. |
| `backend/app/schemas.py` | Catalogo documental explicito, campos de minuta por afectacion/ciclo y contrato de subexpediente. | Alinear contratos API con reglas 2C. |
| `backend/app/services/access.py` | Resolutores de acceso por relacion documental dinamica. | Evitar IDOR y conservar pertenencia territorial. |
| `backend/app/routers/documentos.py` | Autorizacion territorial para versiones, descarga, carga y baja logica. | Proteger documentos en todas sus operaciones. |
| `backend/app/services/minutas.py` y `backend/app/routers/minutas.py` | Validaciones de pertenencia, filtros por afectacion y acceso territorial. | Separar minutas compartidas y propias sin duplicacion. |
| `backend/app/main.py` | Filtros por afectacion/ciclo y endpoint agregado de subexpediente. | Exponer la navegacion operativa 2C desde backend. |
| `backend/app/routers/pagos.py` | Filtro de pagos por `id_afectacion`/`id_ciclo_afectacion`. | Aislar pagos en subexpediente. |
| `frontend/src/App.jsx` | Ruta lazy de subexpediente y titulo contextual. | Abrir afectaciones dentro del expediente maestro. |
| `frontend/src/pages/ExpedienteDetail.jsx` | Accion para abrir subexpediente desde la lista de afectaciones. | Hacer navegable el detalle por afectacion. |
| `frontend/src/pages/AfectacionSubexpediente.jsx` | Nueva pagina de subexpediente con tabs de flujo, asambleas, convenios, pagos, minutas, documentos y antecedentes. | Separar vista propia de cada afectacion. |
| `frontend/src/components/fase2/DocumentosPanel.jsx` | Panel parametrizable por tipo/ID de entidad. | Soportar documentos maestros y documentos propios. |
| `frontend/src/components/fase2/MinutasPanel.jsx` | Panel parametrizable para minutas compartidas o propias. | Evitar mezclar minutas entre afectaciones. |
| `frontend/src/components/fase2/PagosPanel.jsx` | Panel con alcance por afectacion. | Mostrar solo pagos/tramites del subexpediente. |
| `frontend/src/components/fase2/FlujoLiberacionPanel.jsx` | Panel con afectacion opcional y actividades compartidas como antecedentes. | Reutilizar flujo 2B dentro del subexpediente. |
| `backend/tests/test_subcorte_2c.py` | Pruebas nuevas de aislamiento documental/operativo y permisos territoriales. | Cubrir la regresion critica de 2C. |
| `ESTADO_PROYECTO.md` | Actualizacion de continuidad con 007, resultados y siguiente paso. | Mantener la fuente principal alineada con lo verificado. |

## 10. Migraciones y compatibilidad

La migracion 007 fue aplicada localmente despues de respaldo:

```text
respaldo: backups/pre_migracion_007_20260804.dump
tamaño:   288K
SHA-256:  2573a276dea8603cc82c519e56f95a92df3a9708b389b63ed53cdf51a8f7e014
migracion: BEGIN -> COMMIT
schema_migrations local: 004, 005, 006, 007
```

Compatibilidad:

- no elimina columnas ni datos;
- no reclasifica documentos historicos;
- no asigna minutas antiguas a afectaciones por inferencia;
- mantiene minutas existentes como compartidas;
- requiere que cada ambiente confirme 006 antes de aplicar 007;
- otros equipos deben respaldar y ejecutar preflight porque sus datos pueden no
  coincidir con la base local vacia de esta maquina.

## 11. Pruebas y validaciones

| Validacion | Comando | Resultado | Estado |
| --- | --- | --- | --- |
| Estado Git inicial | `git status --short` | `ESTADO_PROYECTO.md` modificado por el usuario y propuesta/evaluacion sin seguimiento; se respetaron esos cambios. | Ejecutada |
| Inspeccion de base local | `docker compose exec -T db psql ...` | 004/005/006 aplicadas inicialmente; cero datos operativos locales. | Ejecutada |
| Prueba roja pre-007 | `docker compose exec -T backend pytest tests/test_subcorte_2c.py -q` | 1 fallo esperado por check de `documentacion_soporte` al usar `tramo_nucleo`; 2 pruebas pasaron. | Ejecutada |
| Respaldo pre-007 | `docker compose exec -T db pg_dump ...` | Archivo `backups/pre_migracion_007_20260804.dump`, 288K, SHA-256 verificado. | Ejecutada |
| Migracion 007 | `docker compose exec -T db psql ... < backend/db/migrations/007_subcorte_2c_navegacion_documental.sql` | `BEGIN` -> `COMMIT`; version 007 registrada. | Ejecutada |
| Verificacion de esquema | `docker compose exec -T db psql ... SELECT ...` | `schema_migrations` contiene 004/005/006/007 y `minuta` tiene `id_afectacion`/`id_ciclo_afectacion`. | Ejecutada |
| Pruebas 2C | `docker compose exec -T backend pytest tests/test_subcorte_2c.py -q` | `3 passed, 1 warning`. | Aprobada |
| Suite backend completa | `docker compose exec -T backend pytest -q` | `107 passed, 1 warning`. | Aprobada |
| Lint frontend codigo propio | `docker run --rm software-pa-frontend-2c-validation npx oxlint src` | `Found 0 warnings and 0 errors`. | Aprobada |
| Build frontend | `docker run --rm software-pa-frontend-2c-validation npm run build -- --outDir /tmp/software-pa-frontend-2c-build` | Build de produccion exitoso. | Aprobada |
| Lint frontend script completo | `docker run --rm software-pa-frontend-2c-validation npm run lint` | Fallo por escanear `node_modules` dentro de la imagen temporal, con errores de dependencias de terceros. | No aplicable al codigo propio; riesgo documentado |

## 12. Riesgos restantes

1. Falta aceptacion funcional de usuarios finales sobre el recorrido 2C.
2. La base local validada no contiene datos operativos; ambientes con datos
   reales deben respaldar y ejecutar preflight antes de 007.
3. Documentos historicos asociados a `nucleo_agrario` pueden requerir
   conciliacion manual futura; 2C no los mueve por inferencia.
4. El script `npm run lint` debe ajustarse posteriormente para ignorar
   `node_modules` dentro de imagenes de validacion, aunque `src` paso limpio.
5. La rotacion de secretos expuestos en historial sigue pendiente en Corte 3.

## 13. Actualizacion realizada en `ESTADO_PROYECTO.md`

Se actualizaron:

- proximo trabajo funcional;
- rutas relevantes y contrato HTTP agregado de subexpediente;
- historial de migraciones con 007;
- trabajo realizado del Subcorte 2C;
- estado de base local validada con 004/005/006/007 y cero datos operativos;
- estado del Corte 2;
- trabajo tecnico pendiente;
- instruccion para continuar.

## 14. Estado final

**Implementacion completa y validada.**

Evidencia: la migracion 007 fue aplicada localmente con respaldo previo, el
esquema quedo en 004/005/006/007, la suite backend completa paso con `107
passed`, `npx oxlint src` no reporto errores ni advertencias, y el build
frontend finalizo correctamente. Queda pendiente la aceptacion funcional de
usuarios finales y la validacion por ambiente antes de replicar 007.
