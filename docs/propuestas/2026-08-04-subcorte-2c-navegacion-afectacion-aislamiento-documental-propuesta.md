# Propuesta tecnica - Subcorte 2C: navegacion por afectacion y aislamiento documental

**Fecha:** 2026-08-04

**Estado:** propuesta tecnica; no implementada.

**Alcance:** Corte principal 2, Subcorte 2C.

**Fuente de continuidad:** `ESTADO_PROYECTO.md`.

Esta propuesta se elaboro con revision documental, migraciones, modelos ORM,
schemas, servicios, routers, frontend, pruebas e inspeccion de solo lectura de
la base local activa. No ejecuta migraciones, no modifica la base, no cambia
codigo funcional y no actualiza `ESTADO_PROYECTO.md`.

## 1. Trabajo vigente identificado

El siguiente trabajo funcional vigente es el **Subcorte 2C del Corte principal
2: navegacion por afectacion y aislamiento documental**.

El Subcorte 2A ya separo afectaciones colectivas e individuales. El Subcorte
2B ya agrego ciclos, salidas terminales, secuencia y estados derivados. 2C no
debe reimplementar esos trabajos.

Prerrequisito operativo documentado: antes de implementar 2C debe completarse
la aceptacion funcional de los recorridos 2B con usuarios sobre rutas
colectiva, individual, terminal, modificatorio y expediente mixto.

Objetivo de 2C:

- conservar `tramo_nucleo` como expediente maestro territorial;
- abrir cada `afectacion` en su propio subexpediente operativo;
- mostrar antecedentes compartidos sin duplicarlos;
- aislar actuaciones, asambleas, convenios, tramites, pagos, minutas y
  documentos propios de cada afectacion;
- corregir el uso actual del tipo documental invalido `tramo_nucleo`;
- probar que dos afectaciones del mismo `tramo_nucleo` no mezclan datos.

Quedan fuera de 2C:

- eliminar columnas heredadas;
- redisenar 2B o sus vistas de estado;
- modelar inventario detallado de BDT;
- modelar avaluos;
- derecho de via versionado del Corte 5;
- autenticacion formal del Corte 4.

## 2. Estado actual verificado

### Documentacion funcional

`docs/Descripción proceso.md` y `docs/Flujo liberacion derechos.md` confirman
la jerarquia:

```text
Proyecto -> Tramo -> Tramo_Nucleo -> Afectacion
```

`tramo_nucleo` conserva investigacion, sensibilizacion, caminamiento y contexto
compartido. `afectacion` nace solo cuando estan confirmados derecho,
superficie, geometria y sujetos.

El PDF `flujograma propiedad social.pdf` no aparece con ese nombre en el
repositorio. Solo se encontro `docs/TREN MAYA - Universo de trabajo,
programacion y Acciones realizadas_03NOV.pdf`. Por tanto, la lectura directa
del flujograma canónico no fue verificable en esta auditoria; se uso su
resumen versionado en `docs/Descripción proceso.md` y `docs/Flujo liberacion
derechos.md`.

### Base activa

Se ejecuto inspeccion de solo lectura mediante `docker compose exec -T db
psql ... -c SELECT`. Resultado:

```text
schema_migrations: 004, 005, 006
afectaciones: 0 totales / 0 activas
documentos activos por tipo: 0
documentos con tipo invalido: 0
asambleas activas sin afectacion: 0
actividades cop_original compartidas: 0
actividades posteriores sin ciclo: 0
afectaciones activas sin ciclo original: 0
```

La fotografia de datos operativos registrada en `ESTADO_PROYECTO.md`
corresponde a la base local de referencia de otro equipo. En esta maquina se
verifico el mismo nivel de esquema (`004`, `005`, `006`), pero sin datos
operativos locales. Por tanto, la continuidad funcional se toma de
`ESTADO_PROYECTO.md`, mientras que la compatibilidad de datos debe verificarse
por ambiente antes de ejecutar cualquier migracion.

### Modelo de datos y migraciones

Implementado:

- `afectacion` tiene `tipo_salida_terminal`, `fecha_salida_terminal` y
  `motivo_salida_terminal`.
- `afectacion_ciclo` existe como identidad estable de ciclos.
- `actividad_campo` tiene `id_ciclo_afectacion` nullable. En `cop_original`
  puede permanecer nulo para antecedentes compartidos.
- `asamblea`, `convenio` y `tramite_fifonafe` ya tienen `id_afectacion` e
  `id_ciclo_afectacion`.
- `pago_indemnizacion` se relaciona con `tramite_fifonafe`; por esa cadena se
  puede aislar por afectacion y ciclo.
- `documentacion_soporte` solo acepta `nucleo_agrario`, `afectacion`,
  `convenio` u `orv`.
- `documento_version` conserva versiones inmutables con SHA-256 calculado por
  servidor.
- 006 crea vistas `vw_afectacion_ciclo_estado`, `vw_afectacion_estado`,
  `vw_tramo_nucleo_estado` y `vw_dashboard_liberacion`.

Pendiente para 2C:

- no existe ruta frontend para
  `/expedientes/:id_tramo_nucleo/afectaciones/:id_afectacion`;
- los listados principales siguen consultando por `id_tramo_nucleo`;
- `documentacion_soporte` no puede representar documentos del expediente
  maestro `tramo_nucleo`;
- `DocumentosPanel.jsx` intenta usar `entidad_relacionada_tipo =
  'tramo_nucleo'`, que PostgreSQL rechaza;
- `minuta` solo pertenece a `tramo_nucleo` y opcionalmente a
  `actividad_campo`; no puede marcar una minuta exclusiva de afectacion sin
  inferirla indirectamente;
- varios routers de documentos/minutas no aplican aun autorizacion territorial
  al resolver la entidad relacionada.

### Backend

`backend/app/services/access.py` ya contiene helpers de autorizacion por tramo,
`tramo_nucleo`, afectacion y nucleo. `main.py` los usa en afectaciones,
asambleas, convenios, FIFONAFE y parte de flujo.

Debilidades verificadas:

- `GET /api/documentacion` lista documentos sin resolver pertenencia
  territorial de la entidad dinamica.
- `POST /api/documentacion` crea documentos sin validar la entidad relacionada
  en la capa de aplicacion; depende del trigger, que no controla permisos.
- descarga, versiones y baja de documentos validan existencia del documento,
  pero no autorizacion territorial sobre la entidad relacionada.
- `routers/minutas.py` lista, obtiene, crea, actualiza y elimina minutas sin
  aplicar `require_tramo_nucleo_access`.
- `GET /api/asambleas`, `GET /api/convenios`, `GET /api/fifonafe` no exponen
  filtro por `id_afectacion`, aunque sus tablas ya lo soportan.
- `GET /api/pagos-indemnizacion` solo filtra por `id_tramite_fifonafe`; para
  un subexpediente obliga a cargar tramites por `tramo_nucleo` y filtrar en
  cliente.

### Frontend

`frontend/src/App.jsx` solo registra:

```text
/expedientes
/expedientes/:id_tramo_nucleo
```

`frontend/src/pages/ExpedienteDetail.jsx` carga afectaciones, asambleas y
convenios por `id_tramo_nucleo` y muestra todo en una pantalla maestra. Las
filas de afectacion permiten editar o crear convenio, pero no abrir un
subexpediente.

`frontend/src/components/fase2/DocumentosPanel.jsx` consulta y crea documentos
con `entidad_tipo = 'tramo_nucleo'` / `entidad_relacionada_tipo =
'tramo_nucleo'`. Ese valor no es valido en la restriccion actual de
PostgreSQL.

`PagosPanel.jsx`, `MinutasPanel.jsx` y `FlujoLiberacionPanel.jsx` operan
principalmente por `id_tramo_nucleo`. `FlujoLiberacionPanel` muestra estados
por afectacion, pero dentro del expediente maestro y sin ruta aislada.

### Pruebas

Existe cobertura para 2A y 2B, incluyendo ciclos, terminalidad, modificatorios,
pagos y algunos casos de autorizacion territorial. No se encontro cobertura
para:

- documento de afectacion A no visible en afectacion B del mismo
  `tramo_nucleo`;
- pagos de afectacion A no listados en afectacion B;
- asambleas/convenios/tramites filtrados por `id_afectacion`;
- documentos con autorizacion resuelta desde `afectacion`, `convenio`, `orv`,
  `nucleo_agrario` o futuro `tramo_nucleo`;
- navegacion React al subexpediente.

## 3. Reglas funcionales confirmadas

1. `tramo_nucleo` no se elimina; es el expediente maestro territorial.
2. `afectacion` es el subexpediente operativo confirmado.
3. Sensibilizacion y caminamiento originales permanecen en `tramo_nucleo` y
   se muestran como antecedentes compartidos.
4. Actividades de ciclos posteriores pertenecen al ciclo de una afectacion.
5. ORV pertenece al nucleo; no se duplica por afectacion.
6. Las asambleas aplican solo a derechos colectivos.
7. Los convenios siempre pertenecen a una afectacion.
8. FIFONAFE y pagos se aislan por la cadena
   `afectacion -> afectacion_ciclo -> convenio -> tramite_fifonafe ->
   pago_indemnizacion`.
9. Documentos son inmutables por version.
10. Las salidas terminales se representan por afectacion y detienen el flujo
    ordinario.
11. La liberacion se deriva despues del pago aplicable, no por RAN.
12. No deben inferirse relaciones historicas ambiguas entre minutas,
    actividades y afectaciones.
13. Toda escritura auditable debe usar `set_audit_context`.
14. Las operaciones compuestas deben confirmarse en una sola transaccion.
15. Toda lectura/escritura debe conservar autorizacion por rol y pertenencia
    territorial.

## 4. Hallazgos y contradicciones

| ID | Hallazgo | Consecuencia | Estado |
| --- | --- | --- | --- |
| H-01 | `DocumentosPanel.jsx` usa `tramo_nucleo`, pero `documentacion_soporte` lo rechaza. | El panel documental del expediente falla al crear/listar documentos del maestro. | Contradiccion confirmada |
| H-02 | La continuidad funcional exige documentos compartidos del expediente maestro, pero el esquema solo admite nucleo, afectacion, convenio y ORV. | Usar `nucleo_agrario` mezclaria documentos entre tramos distintos del mismo nucleo. | Ajuste tecnico requerido |
| H-03 | La pantalla maestra mezcla asambleas, pagos, minutas y documentos de todas las afectaciones. | Usuarios pueden interpretar como propio de una afectacion lo que pertenece a otra. | Pendiente 2C |
| H-04 | No hay ruta de subexpediente en React. | La jerarquia aprobada no esta representada en navegacion. | Pendiente 2C |
| H-05 | `minuta` no tiene `id_afectacion` ni `id_ciclo_afectacion`. | No se puede crear una minuta exclusiva de afectacion sin una relacion indirecta o ambigua. | Ajuste tecnico requerido |
| H-06 | Documentos y minutas no resuelven autorizacion territorial desde la entidad consultada. | Riesgo de acceso fuera de tramo asignado. | Seguridad pendiente |
| H-07 | Listados backend carecen de filtros por `id_afectacion` en asambleas, convenios, FIFONAFE y pagos. | El aislamiento depende del frontend, no del contrato de API. | Pendiente 2C |
| H-08 | Esta base local tiene 006 aplicada pero cero datos operativos; la fotografia de `ESTADO_PROYECTO.md` pertenece a otra base local de referencia. | No puede validarse aislamiento con datos reales en esta maquina; se requieren fixtures sinteticos y verificacion por ambiente. | Contexto de ambiente confirmado |

## 5. Diseno propuesto

### Principio

2C debe separar **navegacion y consulta operativa** sin trasladar datos
compartidos ni duplicar antecedentes.

Se proponen dos niveles:

```text
/expedientes/:id_tramo_nucleo
  Expediente maestro: contexto territorial, ORV, padron, antecedentes
  compartidos, documentos maestros y lista de afectaciones.

/expedientes/:id_tramo_nucleo/afectaciones/:id_afectacion
  Subexpediente: datos de la afectacion, antecedentes compartidos visibles
  en modo lectura, ciclos, asambleas aplicables, convenios, RAN, FIFONAFE,
  pagos, minutas propias, documentos propios y cierre.
```

### Propiedad de datos

| Dato | Dueno | Visibilidad en maestro | Visibilidad en subexpediente |
| --- | --- | --- | --- |
| Proyecto, tramo, nucleo, tramo_nucleo | `tramo_nucleo` y relacionados | Completa | Encabezado contextual |
| ORV y padron | `nucleo_agrario`, `orv`, `padron_historial` | Completa | Solo contexto/antecedente |
| Sensibilizacion y caminamiento `cop_original` sin ciclo | `actividad_campo` con `id_ciclo_afectacion IS NULL` | Completa | Antecedente compartido de solo lectura |
| Actividades posteriores | `actividad_campo.id_ciclo_afectacion` | Resumen agregado | Solo si el ciclo pertenece a la afectacion |
| Afectacion | `afectacion` | Lista/resumen | Completa |
| Asamblea | `asamblea.id_afectacion` + `id_ciclo_afectacion` | Resumen por afectacion | Propia; solo colectiva |
| Convenio/RAN | `convenio.id_afectacion` + `id_ciclo_afectacion` | Resumen | Propio |
| FIFONAFE | `tramite_fifonafe.id_afectacion` + `id_ciclo_afectacion` | Resumen | Propio |
| Pagos | por `tramite_fifonafe` | Resumen agregado | Solo pagos de tramites de la afectacion |
| Minutas compartidas | `minuta.id_afectacion IS NULL` | Completa | Antecedente si se decide mostrar |
| Minutas propias | nueva relacion `minuta.id_afectacion` + `id_ciclo_afectacion` | Resumen | Completa |
| Documentos maestros | `documentacion_soporte` tipo `tramo_nucleo` | Completa | Antecedente opcional |
| Documentos propios | `documentacion_soporte` tipo `afectacion` o `convenio` | Conteo/resumen | Completa |

### Comportamiento esperado

1. Al abrir el expediente maestro se muestran datos territoriales, estado
   agregado 2B, antecedentes compartidos y tarjetas de afectaciones.
2. Cada tarjeta de afectacion tiene accion **Abrir subexpediente**.
3. Al abrir un subexpediente, el backend valida que `id_afectacion` exista,
   este activa, pertenezca a `id_tramo_nucleo` y este dentro de los tramos del
   usuario.
4. El subexpediente muestra antecedentes compartidos como antecedentes, no como
   registros propios.
5. Asambleas, convenios, tramites, pagos, documentos y minutas propias se
   filtran por `id_afectacion`.
6. Para afectacion individual no se muestra ni permite capturar asamblea de
   anuencia o retiro de fondos.
7. Para afectacion terminal se bloquean acciones ordinarias y se conservan
   notas, documentos y trazabilidad.
8. El panel documental del subexpediente crea documentos con
   `entidad_relacionada_tipo = 'afectacion'` e `entidad_relacionada_id =
   id_afectacion`.
9. El panel documental del expediente maestro no debe usar `nucleo_agrario`
   para simular `tramo_nucleo`, porque eso mezcla cruces territoriales.

### Estados y transiciones

2C consume los estados de 2B; no introduce nuevos estados persistidos.

Transiciones de navegacion:

```text
expediente maestro
  -> abrir afectacion activa
  -> validar pertenencia id_tramo_nucleo/id_afectacion
  -> cargar subexpediente
  -> volver al expediente maestro
```

Transiciones de escritura:

- documentos maestros: con `tramo_nucleo` como tipo documental valido;
- documentos propios: siempre por `afectacion` o `convenio`;
- minutas compartidas: siguen en `tramo_nucleo`;
- minutas propias: requieren afectacion y ciclo explicitos;
- pagos: se crean contra tramite de indemnizacion y se muestran solo en la
  afectacion dueña del tramite.

## 6. Cambios por capa

| Archivo o componente | Problema | Solucion | Justificacion | Dependencias | Riesgo | Validacion |
| --- | --- | --- | --- | --- | --- | --- |
| `backend/db/migrations/007_subcorte_2c_navegacion_documental.sql` | El esquema no representa documentos de `tramo_nucleo` ni minutas propias de afectacion. | Migracion expansiva: admitir `tramo_nucleo` en `documentacion_soporte`; extender trigger dinamico; agregar `minuta.id_afectacion` e `id_ciclo_afectacion` nullable con FK compuesta; indices por afectacion/ciclo. | Permite distinguir documento maestro de documento de afectacion sin usar `nucleo_agrario` como sustituto. | Migracion 006 aplicada. | Incompatibilidad si otros ambientes tienen checks con nombres distintos. | Prevalidacion de constraints, prueba SQL de tipos validos/invalidos, rollback en copia. |
| `backend/app/models.py` | ORM no refleja minutas por afectacion ni tipo documental `tramo_nucleo`. | Agregar columnas nullable en `Minuta`; no cambiar `DocumentacionSoporte` salvo validaciones de aplicacion. | Mantiene compatibilidad con filas existentes. | Migracion 007. | Desfase ORM/esquema si no se aplica migracion. | Pruebas de modelo y suite backend. |
| `backend/app/schemas.py` | `DocumentacionSoporteCreate.entidad_relacionada_tipo` es `str`; minutas no aceptan afectacion/ciclo. | Usar `Literal['tramo_nucleo','nucleo_agrario','afectacion','convenio','orv']`; agregar campos opcionales a `MinutaCreate/Response`. | Contratos fallan temprano y reducen errores SQL. | Migracion 007. | Consumidores antiguos que envian valores invalidos empezaran a recibir 422. | Pruebas de validacion Pydantic. |
| `backend/app/services/access.py` | Falta resolver autorizacion desde entidades documentales dinamicas. | Agregar `require_document_relation_access(db,user,tipo,id)` y `require_document_access(db,user,id_documento)`. | Evita confiar en IDs enviados por cliente y cierra IDOR. | Helpers actuales. | Resolver ORV requiere ir de ORV a nucleo y nucleo a tramo permitido. | Tests 403/200 por tipo. |
| `backend/app/main.py` - documentacion | Listar/crear documentos no valida territorio ni relacion funcional. | Reubicar logica a servicio/router; exigir filtro explicito; resolver acceso antes de consultar/crear; errores publicos estables. | Documentos son sensibles y deben aislarse por entidad real. | `require_document_relation_access`. | Cambia comportamiento de listado global no filtrado. | Tests de listado por afectacion A/B y acceso cruzado. |
| `backend/app/routers/documentos.py` | Versiones, descargas y baja validan existencia pero no territorio. | Usar `require_document_access` antes de listar versiones, descargar, subir o dar baja. | El archivo fisico hereda permisos del documento. | Servicio de acceso documental. | Ninguno funcional si permisos estan bien asignados. | Tests de descarga 403 fuera de tramo. |
| `backend/app/routers/minutas.py` y `services/minutas.py` | Minutas carecen de autorizacion territorial y no pueden aislarse por afectacion. | Aplicar `require_tramo_nucleo_access`; agregar filtro `id_afectacion`; validar que afectacion/ciclo pertenezcan al `tramo_nucleo`. | Evita mezcla de minutas propias y compartidas. | Migracion de `minuta`. | Filas existentes quedan compartidas. | Tests de minuta compartida vs propia. |
| `backend/app/main.py` - asambleas | Listado solo filtra por `id_tramo_nucleo`. | Agregar filtros `id_afectacion` e `id_ciclo_afectacion`; validar pertenencia cuando se indiquen. | El subexpediente colectivo no debe ver asambleas de otra afectacion. | Columnas de 006. | Ninguno para consumidores actuales. | Tests con dos colectivas mismo expediente. |
| `backend/app/main.py` - convenios | Listado solo filtra por `id_tramo_nucleo`. | Agregar filtros `id_afectacion` e `id_ciclo_afectacion`. | Aisla COP/RAN por afectacion. | Columnas existentes. | Bajo. | Tests de convenios A/B. |
| `backend/app/main.py` - FIFONAFE | Listado solo filtra por `id_tramo_nucleo`. | Agregar filtros `id_afectacion`, `id_ciclo_afectacion` y `tipo_tramite`. | Aisla no conflictos e indemnizacion. | Columnas existentes. | Bajo. | Tests de tramites A/B. |
| `backend/app/routers/pagos.py` | Pagos solo se filtran por tramite. | Agregar filtros `id_afectacion` e `id_ciclo_afectacion` mediante join con `tramite_fifonafe`. | Permite al subexpediente consultar pagos sin traer todo el expediente. | Columnas existentes. | Bajo. | Tests de pagos A/B. |
| Nuevo servicio `backend/app/services/subexpedientes.py` | El frontend tendria que ensamblar multiples recursos y validar pertenencia. | Agregar `GET /api/tramos-nucleos/{id_tramo_nucleo}/afectaciones/{id_afectacion}/subexpediente` con datos de contexto, estado, antecedentes y links/colecciones principales. | Centraliza validacion y contrato del subexpediente. | Helpers de acceso; vistas 2B. | Respuesta grande si se incluyen todas las colecciones; limitar a resumen y paginar listados. | Test de 404/403/409 por IDs cruzados y respuesta esperada. |
| `frontend/src/App.jsx` | No existe ruta de subexpediente. | Agregar ruta `/expedientes/:id_tramo_nucleo/afectaciones/:id_afectacion`. | Representa la jerarquia aprobada. | Nueva pagina React. | Titulo/topbar debe distinguir maestro/subexpediente. | Build y prueba manual. |
| `frontend/src/pages/ExpedienteDetail.jsx` | Pantalla maestra mezcla detalle operativo. | Convertirla en maestro: datos territoriales, antecedentes compartidos, resumen 2B y lista de afectaciones con boton abrir. | Conserva el expediente maestro sin mezclar actuaciones propias. | Ruta nueva. | Riesgo UX si se ocultan acciones existentes; mantener acciones de alta de afectacion. | Recorrido manual maestro -> subexpediente -> maestro. |
| Nueva pagina `frontend/src/pages/AfectacionSubexpediente.jsx` | No hay vista aislada por afectacion. | Cargar endpoint de subexpediente y renderizar paneles por tipo de derecho. | Superficie operativa natural para convenio, RAN, FIFONAFE, pagos y documentos. | Backend 2C. | Duplicacion de UI si no se parametrizan paneles. | Build y pruebas de regresion visual/manual. |
| `frontend/src/components/fase2/DocumentosPanel.jsx` | Usa tipo invalido y esta acoplado a `idTramoNucleo`. | Parametrizar como `DocumentosPanel({ entidadTipo, entidadId, canWrite })`; en subexpediente usar `afectacion`; en maestro usar `tramo_nucleo`. | Corrige el fallo actual y evita mezcla. | Backend documental 2C. | Requiere migracion 007 antes de habilitar alta documental maestra. | Prueba API/frontend con creacion y carga de version. |
| `frontend/src/components/fase2/PagosPanel.jsx` | Carga tramites y pagos por expediente completo. | Aceptar `idAfectacion`; consultar `/fifonafe?id_afectacion=...` y `/pagos-indemnizacion?id_afectacion=...`. | Evita filtrar datos sensibles en cliente. | Filtros backend. | Bajo. | Caso con dos afectaciones y pagos separados. |
| `frontend/src/components/fase2/MinutasPanel.jsx` | Solo muestra minutas de `tramo_nucleo`. | Modo maestro: minutas compartidas. Modo subexpediente: minutas propias y, separado, antecedentes compartidos si aplica. | No duplica ni infiere minutas. | Migracion de minutas. | Decidir si los antecedentes compartidos son solo lectura. | Test manual y backend. |
| `frontend/src/components/fase2/FlujoLiberacionPanel.jsx` | Muestra todas las afectaciones dentro del maestro. | Agregar modo `idAfectacion` para renderizar una sola afectacion; mantener modo maestro como resumen. | Reutiliza estados 2B sin mezclar. | Endpoint de estado existente. | Refactor de componente largo. | Lint/build. |

## 7. Migracion y compatibilidad

Se propone una migracion expansiva `007_subcorte_2c_navegacion_documental.sql`.

Orden:

1. `BEGIN` y `pg_advisory_xact_lock`.
2. Verificar `schema_migrations` con version `006`.
3. Resolver usuario tecnico activo y establecer `app.current_user_id`.
4. Prevalidar:
   - no existen documentos activos con tipos fuera del catalogo vigente;
   - si se agregan columnas a `minuta`, no se intenta poblarlas por inferencia;
   - no hay constraints con nombres inesperados que impidan reemplazo seguro.
5. Reemplazar el `CHECK` de `documentacion_soporte.entidad_relacionada_tipo`
   para incluir `tramo_nucleo`.
6. Reemplazar `fn_validar_documentacion_soporte_referencia()` para validar
   tambien `tramo_nucleo`.
7. Agregar a `minuta`:
   - `id_afectacion INTEGER NULL`;
   - `id_ciclo_afectacion INTEGER NULL`;
   - FK compuesta `(id_tramo_nucleo, id_ciclo_afectacion, id_afectacion)` hacia
     `afectacion_ciclo`;
   - `CHECK` que obliga ambos campos nulos o ambos presentes.
8. Crear indices:
   - `idx_2c_documentacion_tipo_id`;
   - `idx_2c_minuta_afectacion`;
   - `idx_2c_minuta_ciclo`.
9. Registrar `007` en `schema_migrations`.
10. `COMMIT`.

Compatibilidad:

- Las minutas existentes quedan compartidas porque sus nuevas columnas son
  nulas.
- No se migran documentos de `nucleo_agrario` a `tramo_nucleo`.
- No se infieren documentos de afectacion por fecha, convenio o nombre.
- En esta base local no hay documentos ni afectaciones; en otros ambientes se
  debe inspeccionar antes de aplicar.
- No se usa `nucleo_agrario` como sustituto de `tramo_nucleo`: un mismo nucleo
  puede participar en varios cruces territoriales y esa sustitucion mezclaria
  expedientes maestros distintos.

## 8. Seguridad, autorizacion e integridad

Autorizacion:

- Admin conserva acceso completo.
- Operador/visualizador/geografo solo leen recursos dentro de tramos asignados
  por `usuario_tramo`.
- Escrituras ordinarias siguen limitadas a roles existentes (`admin`,
  `operador`) salvo decision explicita sobre documentos de geografo.
- El backend debe resolver territorio desde la entidad persistida, no desde
  parametros de cliente.

Integridad:

- La pertenencia `id_tramo_nucleo` / `id_afectacion` se valida por FK
  compuesta o por servicio antes de insertar.
- Documentos con entidad dinamica mantienen trigger PostgreSQL.
- Minutas propias requieren afectacion y ciclo; minutas compartidas no deben
  fingir pertenencia a una afectacion.
- Pagos se aislan por la cadena real del tramite, no por IDs enviados por el
  cliente.
- Toda escritura usa `set_audit_context` antes del `commit`.
- No hay bajas fisicas; se conserva baja logica y versiones documentales
  inmutables.

Errores:

- Violaciones de reglas se traducen a mensajes de dominio estables.
- No se debe devolver SQL ni `str(exc)` al cliente.

## 9. Plan incremental de implementacion

1. Confirmar aceptacion funcional de 2B como gate previo de implementacion.
2. Agregar pruebas backend esperadas para aislamiento por afectacion, primero
   en rojo.
3. Implementar migracion 007 en copia de base y validar rollback/restauracion.
4. Actualizar ORM y schemas.
5. Agregar helpers de autorizacion documental y aplicarlos en documentos y
   minutas.
6. Agregar filtros backend por `id_afectacion`/`id_ciclo_afectacion`.
7. Crear endpoint agregado de subexpediente.
8. Parametrizar paneles React.
9. Crear ruta y pagina `AfectacionSubexpediente.jsx`.
10. Ajustar `ExpedienteDetail.jsx` para vista maestra y boton de apertura.
11. Ejecutar suite backend, lint frontend y build.
12. Ejecutar recorrido manual con dos afectaciones en el mismo
    `tramo_nucleo`, una colectiva y una individual.
13. Aplicar migracion a base activa solo con respaldo previo, backend/scheduler
    detenidos y `ON_ERROR_STOP=1`.
14. Actualizar `ESTADO_PROYECTO.md` solo despues de validacion funcional.

## 10. Matriz de pruebas

| Capa | Caso | Resultado esperado |
| --- | --- | --- |
| SQL | Crear documento `tramo_nucleo`. | Inserta si el expediente existe y esta activo. |
| SQL | Crear documento con tipo desconocido. | Rechazo por `CHECK`. |
| SQL | Crear minuta propia con afectacion/ciclo de otro expediente. | Rechazo por FK compuesta. |
| SQL | Crear minuta con solo `id_afectacion` o solo `id_ciclo_afectacion`. | Rechazo por `CHECK`. |
| API | `GET /documentacion?entidad_tipo=afectacion&entidad_id=A`. | Devuelve solo documentos de A. |
| API | Documento de A consultado por usuario sin tramo. | 403 sin revelar datos internos. |
| API | Documento de convenio usa permisos del convenio y su `tramo_nucleo`. | 200/403 segun adscripcion. |
| API | Dos afectaciones del mismo `tramo_nucleo` con documentos distintos. | A no ve documentos de B. |
| API | `GET /asambleas?id_afectacion=A`. | Solo asambleas de A; individual sin asambleas de anuencia. |
| API | `GET /convenios?id_afectacion=A`. | Solo convenios de A. |
| API | `GET /fifonafe?id_afectacion=A`. | Solo tramites de A. |
| API | `GET /pagos-indemnizacion?id_afectacion=A`. | Solo pagos de tramites de A. |
| API | `GET /tramos-nucleos/T/afectaciones/A/subexpediente` con A de otro T. | 404 o 409 publico; no entrega datos. |
| API | Subexpediente terminal. | Permite documentos/notas; no acciones ordinarias. |
| Frontend | Abrir expediente maestro. | Muestra antecedentes y lista de afectaciones, sin mezclar detalle operativo. |
| Frontend | Abrir subexpediente colectivo. | Muestra asambleas, convenios, pagos y documentos solo de esa afectacion. |
| Frontend | Abrir subexpediente individual. | No muestra alta de asamblea de anuencia/retiro. |
| Frontend | Crear documento desde subexpediente. | Envia `entidad_relacionada_tipo='afectacion'`. |
| Frontend | Crear documento maestro. | Envia `entidad_relacionada_tipo='tramo_nucleo'`. |
| Regresion | Suite 2A/2B completa. | Sin regresiones en integridad, estados ni pagos. |

## 11. Riesgos y mitigaciones

| Riesgo | Mitigacion |
| --- | --- |
| Autorizar `tramo_nucleo` en documentos cambia el catalogo historico de tipos documentales. | Hacerlo solo mediante migracion 007 expansiva, sin reclasificar documentos existentes; la justificacion funcional es evitar mezcla por nucleo cuando hay varios tramos. |
| Refactor frontend amplio puede romper flujos ya capturados en maestro. | Parametrizar paneles incrementalmente y conservar ruta maestra. |
| Datos historicos en otros ambientes pueden tener minutas o documentos que usuarios consideran de una afectacion. | No inferir; crear reporte de conciliacion manual posterior. |
| Listados actuales sin filtro pueden ser usados por pantallas existentes. | Mantener compatibilidad para admin y exigir filtros solo donde el riesgo de acceso sea alto; migrar frontend primero. |
| Documentos fisicos pueden quedar accesibles si solo se protege metadata. | Validar permisos tambien en descargas de archivo y versiones. |
| Pruebas locales con base vacia no prueban casos reales. | Usar fixtures con dos afectaciones en el mismo expediente y validar en copia de datos representativa antes de produccion. |

## 12. Criterios de aceptacion

1. Existe ruta frontend
   `/expedientes/:id_tramo_nucleo/afectaciones/:id_afectacion`.
2. Abrir una afectacion que no pertenece al `tramo_nucleo` de la URL no muestra
   datos.
3. El expediente maestro conserva datos territoriales, ORV, antecedentes
   compartidos y lista de afectaciones.
4. El subexpediente muestra solo actuaciones propias de su afectacion y los
   antecedentes compartidos claramente separados.
5. El panel documental del subexpediente usa `afectacion`, nunca
   `tramo_nucleo`.
6. El panel documental maestro usa `tramo_nucleo` y PostgreSQL lo acepta.
7. Dos afectaciones del mismo `tramo_nucleo` no mezclan documentos, pagos,
   convenios, asambleas, FIFONAFE ni minutas propias.
8. Las afectaciones individuales no muestran acciones de asamblea colectiva.
9. Las afectaciones terminales conservan trazabilidad/documentos y bloquean
   acciones ordinarias.
10. Todas las escrituras auditables establecen contexto de auditoria.
11. Lecturas y escrituras respetan rol y pertenencia territorial.
12. Suite backend, lint frontend y build de produccion pasan.

## 13. Actualizaciones previstas para `ESTADO_PROYECTO.md`

Despues de una implementacion validada, actualizar:

- **Ultima actualizacion** con la fecha real.
- **Proximo trabajo funcional** para mover 2C a implementado y senalar el
  siguiente paso.
- **Rutas relevantes** con la nueva pagina de subexpediente y componentes
  parametrizados.
- **Contratos HTTP relevantes** con filtros nuevos y endpoint agregado.
- **Historial de migraciones** agregando 007 si se implementa.
- **Trabajo realizado / Corte principal 2** con evidencia de pruebas, lint,
  build y validacion de aislamiento.
- **Estado de la base local validada / estados por ambiente** para aclarar que
  la fotografia operativa de `ESTADO_PROYECTO.md` corresponde a otra base local
  de referencia y que esta maquina solo verifico esquema 006 sin datos
  operativos.
- **Trabajo tecnico transversal pendiente** con cualquier conciliacion manual
  de documentos/minutas historicas que quede pendiente.

No actualizar `docs/historico/Adaptaciones 2.0 - Implementacion.md`; es un
registro cerrado.

## 14. Decisiones y confirmaciones

| ID | Decision o confirmacion | Recomendacion | Motivo |
| --- | --- | --- | --- |
| D-01 | Admitir `tramo_nucleo` como `entidad_relacionada_tipo` valido en `documentacion_soporte`. | Confirmado por continuidad funcional; implementar como ajuste tecnico de 2C. | Es la unica forma precisa de documentos del expediente maestro sin mezclarlos por nucleo. |
| D-02 | Alcance de minutas propias de afectacion. | Confirmar tecnicamente columnas nullable `id_afectacion` e `id_ciclo_afectacion` en `minuta`. | Evita inferir por actividad, fecha o asunto. |
| D-03 | Listado global de documentos para no admin. | Restringirlo: exigir entidad explicita o resolver por tramos autorizados. | Reduce riesgo de IDOR y fuga documental. |
| D-04 | Permiso de escritura documental para `geografo`. | No cambiar la matriz de roles en 2C; agregar pertenencia territorial y dejar politica fina para Corte 3/4. | El codigo actual tiene permisos documentales mixtos; corregirlos funcionalmente excede el alcance de navegacion/aislamiento. |
| D-05 | Subexpediente agregado vs multiples llamadas frontend. | Crear endpoint agregado de resumen y mantener listados paginables separados. | Centraliza validacion de pertenencia sin respuestas excesivas. |
