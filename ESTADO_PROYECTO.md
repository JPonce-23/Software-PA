# ESTADO DEL PROYECTO — SOFTWARE-PA

> **Documento de continuidad para personas y agentes de IA.**
> Leer completo antes de proponer o modificar código. No asumir que la
> numeración de las fases operativas, los cortes principales y los subcortes de
> Adaptaciones 2.0 significan lo mismo.
>
> **Fuente única de continuidad del proyecto:** este archivo concentra el
> estado actual, las decisiones aprobadas y el trabajo futuro. La fuente
> funcional del proceso es el flujograma de propiedad social, resumido en
> `docs/Descripción proceso.md`; el esquema ejecutable se determina por las
> migraciones aplicadas. Los detalles de los subcortes A, B y C ya ejecutados
> se conservan únicamente como registro cerrado en
> `docs/historico/Adaptaciones 2.0 - Implementación.md`; ese archivo no es un
> segundo roadmap ni debe actualizarse con prioridades posteriores.

**Última actualización:** 5 de agosto de 2026

**Rama de trabajo:** `feature/backend-logica`

**Próximo trabajo funcional:** completar la contracción y aceptación operativa
del Corte 4 de autenticación formal: validar cookies `Secure` detrás del TLS
real, inventariar consumidores bearer, retirar JWT cuando sea compatible y
ejecutar aceptación funcional en navegador. La rotación local de PostgreSQL,
PgAdmin y `SECRET_KEY` fue reportada como realizada antes del trabajo del 5 de
agosto de 2026. No registrar sus valores.

## 1. Objetivo y dominio

SOFTWARE-PA gestiona el seguimiento de la liberación de derecho de vía
ferroviario exclusivamente sobre propiedad social, para derechos colectivos e
individuales. Integra información territorial, agraria, jurídica, social,
documental, financiera y geoespacial.

Quedan fuera del alcance funcional actual la propiedad privada, el catastro y
el Registro Público de la Propiedad. La expropiación directa y la comunidad
indígena tampoco son procesos gestionados por la PA: sólo se registra que una
afectación o, cuando corresponda, el núcleo completo quedó en uno de esos
supuestos y se detiene su seguimiento ordinario.

La jerarquía territorial aprobada es:

```text
Proyecto → Tramo → Tramo_Núcleo
```

`tramo_nucleo` representa el cruce territorial de un tramo con un núcleo
agrario. Es el expediente maestro territorial de la liberación de derecho de
vía en ese cruce y no debe eliminarse ni reducirse a un selector.
`afectacion` representa cada subexpediente operativo confirmado, colectivo o
individual, que nace dentro de él.

La investigación de posibles afectaciones, la sensibilización y el
caminamiento ocurren dentro del expediente maestro y cronológicamente antes
de crear un subexpediente de afectación.
`afectacion` se crea únicamente cuando ya se confirmaron el derecho afectado,
la superficie, la geometría y los sujetos. Una vez creada, su subexpediente
debe mostrar las actuaciones compartidas aplicables como antecedentes, sin
trasladarlas ni duplicarlas fuera de `tramo_nucleo`.

```text
Proyecto
└── Tramo
    └── Tramo_Núcleo                 expediente maestro territorial
        └── Afectación               subexpediente operativo confirmado
            ├── colectiva
            └── individual
```

## 2. Stack y rutas relevantes

- Backend: FastAPI, SQLAlchemy, Pydantic y Python.
- Base de datos: PostgreSQL 15 con PostGIS.
- Frontend: React 19, Vite, Axios, React Router y Leaflet.
- Infraestructura local: Docker Compose.

Rutas principales del repositorio:

```text
backend/app/main.py                     ensamblaje y endpoints heredados
backend/app/models.py                   modelos ORM
backend/app/schemas.py                  contratos Pydantic
backend/app/routers/                    routers de Adaptaciones 2.0
backend/app/services/                   servicios transaccionales
backend/app/jobs/alertas_scheduler.py   tarea diaria de alertas
backend/db/migrations/003_*.sql         Proyecto y retiro de Frente
backend/db/migrations/004_*.sql         Adaptaciones 2.0
backend/db/migrations/005_*.sql         Integridad de afectaciones 2A
backend/db/migrations/006_*.sql         Secuencia y estados de liberación 2B
backend/db/migrations/007_*.sql         Navegación y aislamiento documental 2C
backend/db/migrations/008_*.sql         Autenticación formal y sesiones
backend/db/migrations/009_*.sql         Auditoría de expiración de sesión
backend/tests/                          regresión e integración
backend/app/routers/authentication.py   endpoints de sesión y revocación
backend/app/services/authentication.py  reglas transaccionales de autenticación
backend/app/routers/flujo.py            transiciones explícitas de 2B
backend/app/services/flujo.py           dominio transaccional de 2B
backend/app/services/access.py          autorización territorial
frontend/src/pages/ExpedienteDetail.jsx expediente actual por tramo_nucleo
frontend/src/pages/AfectacionSubexpediente.jsx subexpediente por afectacion
frontend/src/pages/ExpedientesList.jsx  listado actual de tramo_nucleo
frontend/src/components/fase2/          módulos agregados en Adaptaciones 2.0
frontend/src/components/fase2/FlujoLiberacionPanel.jsx flujo mínimo de 2B
```

Contratos HTTP relevantes ya existentes:

```text
GET/POST       /api/proyectos
GET/POST       /api/tramos
GET/POST       /api/tramos-nucleos
GET/POST       /api/afectaciones
GET             /api/afectaciones/{id_afectacion}
POST            /api/afectaciones/colectivas
POST            /api/afectaciones/individuales
PUT             /api/afectaciones/colectivas/{id_afectacion}
PUT             /api/afectaciones/individuales/{id_afectacion}
GET/POST       /api/convenios
GET/POST       /api/asambleas
GET/POST       /api/actividades-campo
GET/POST       /api/fifonafe
GET/POST       /api/personas
POST            /api/parcelas/con-titular
POST            /api/orvs/con-integrantes
GET/POST       /api/minutas
GET/POST       /api/pagos-indemnizacion
GET/POST       /api/afectaciones/{id_afectacion}/ciclos
GET             /api/afectaciones/{id_afectacion}/estado
GET             /api/tramos-nucleos/{id_tramo_nucleo}/estado
GET             /api/tramos-nucleos/{id_tramo_nucleo}/afectaciones/{id_afectacion}/subexpediente
PUT             /api/afectaciones/{id_afectacion}/salida-terminal
POST            /api/fifonafe/{id_tramite}/completar-indemnizacion
POST            /api/asambleas/{id_asamblea}/completar-retiro-fondos
POST            /api/convenios/{id_convenio}/activar-modificatorio
POST            /api/documentacion/{id_documento}/archivo
GET             /api/documentacion/{id_documento}/versiones
GET             /api/alertas/no-vistas
GET             /api/alertas/no-vistas/count
POST            /api/auth/sesiones
GET             /api/auth/sesion
POST            /api/auth/logout
POST            /api/auth/logout-todas
POST            /api/usuarios/{id_usuario}/desbloquear
POST            /api/usuarios/{id_usuario}/revocar-sesiones
```

Los routers se incluyen con prefijo `/api` desde `main.py`. Antes de agregar
una ruta nueva se debe verificar que no exista ya una combinación igual de
método y path en `main.py` o en otro router.

## 3. Documentos que deben leerse

Orden recomendado para recuperar contexto:

1. Este archivo.
2. El flujograma externo `flujograma propiedad social.pdf`, como fuente
   funcional, y su resumen `docs/Descripción proceso.md`.
3. `docs/Flujo liberacion derechos.md`.
4. `docs/Estructura Datos.md`.
5. `docs/Diccionario_Datos_SSALFER.md`.
6. `docs/requirements.md`.
7. Las migraciones `001`, `002`, `003`, `004`, `005` y `006` en orden, como fuente
   del esquema ejecutable.
8. `docs/propuestas/2026-07-31-subcorte-2a-propuesta.md`, como registro de la separación ya
   implementada entre afectaciones colectivas e individuales.
9. `docs/design.md`, con la advertencia de que conserva fragmentos históricos
   y propuestas aún no implementadas.

Cuando se investigue la migración 004 o las decisiones de Adaptaciones 2.0,
consultar adicionalmente
`docs/historico/Adaptaciones 2.0 - Implementación.md`. Es un registro
histórico opcional: sus subcortes A, B y C no son los cortes principales 2, 3
y 4, y cualquier diferencia con este archivo se resuelve a favor de
`ESTADO_PROYECTO.md`.

## 4. Reglas de negocio y técnicas obligatorias

- Revisar autorización por rol y pertenencia territorial en cada operación;
  no confiar en identificadores enviados por el cliente.
- Toda escritura auditable debe establecer el usuario mediante
  `set_audit_context(db, current_user.id_usuario)` antes del `commit`.
- No realizar `DELETE` físico en entidades operativas. La baja lógica registra
  actor, fecha y motivo.
- Las relaciones compuestas deben confirmarse en una sola transacción.
- Las reglas de linaje e integridad importantes deben existir también en
  PostgreSQL mediante FK, `CHECK`, índices o triggers.
- Dinero: `NUMERIC` en PostgreSQL y `Decimal` en Python; nunca `float`.
- Fechas con zona: `datetime.now(timezone.utc)`.
- No devolver `str(exc)` ni detalles internos al cliente. El handler global
  devuelve `Error interno del servidor` y registra el detalle internamente.
- No deduplicar personas solamente por nombre. CURP válida u otra evidencia
  fuerte es necesaria para automatizar una conciliación.
- Los documentos son inmutables por versión: una nueva carga crea un archivo
  y una fila nuevos, con SHA-256 calculado por el servidor.
- Una migración se aplica una sola vez y con `ON_ERROR_STOP=1`, después de un
  respaldo y sin escrituras concurrentes.
- El flujo ordinario debe conservar esta secuencia:
  sensibilización → caminamiento → afectación confirmada → asamblea, sólo
  para derechos colectivos → convenio → RAN → FIFONAFE → pago → liberado.
- Una afectación sólo está `liberada` después de completar el pago del flujo
  aplicable. La inscripción ante el RAN es un avance registral intermedio, no
  el cierre de liberación.
- En derechos individuales, un ciclo concluye cuando su indemnización activa
  está en `completo`. En derechos colectivos exige además una asamblea de
  `retiro_fondos` en `completo` vinculada al mismo ciclo. Alcanzar el límite
  económico o registrar `tipo_pago = total` no presume conclusión.
- `afectacion_ciclo` es la identidad estable de cada COP original o variante.
  El ciclo original nace con la afectación; los ciclos posteriores se abren
  explícitamente y deben ser compatibles con el tipo de derecho.
- Un convenio modificatorio sustituye los importes financieros vigentes de
  su convenio padre; nunca se suma al padre. La activación es transaccional y
  no puede fijar un límite menor que los pagos acumulados del ciclo.
- `expropiacion_directa` y `comunidad_indigena` son salidas terminales fuera
  del seguimiento ordinario. No equivalen a `liberado`, `problema` ni
  `pendiente`; después de marcarlas sólo se permiten trazabilidad, notas y
  documentos.
- La ausencia de tierras de uso común impide la ruta colectiva, pero no debe
  bloquear una afectación individual válida.

Regla financiera:

```text
valor de la tierra       = convenio.monto_100
anticipo de la tierra    = convenio.monto_90, incluido en monto_100
bienes distintos tierra = convenio.monto_bdt
límite base pagable      = monto_100 + monto_bdt, cuando BDT aplica
modificatorio colectivo  = nuevo monto_100 + nuevo monto_bdt
modificatorio individual = nuevo monto_100; monto_bdt está prohibido
```

`monto_90` no se suma de nuevo. Obras complementarias no capturan BDT.

## 5. Historial de migraciones

### 001 — Línea base

Esquema inicial. Fue actualizado históricamente; no usar su estado actual para
deducir qué migraciones tiene aplicada una base persistente.

### 002 — Correcciones de auditoría

Corrige rigor forense, auditoría e integridad de la línea base.

### 003 — Corte principal 1

Archivo:
`backend/db/migrations/003_add_proyecto_drop_frente.sql`

- Crea `proyecto`.
- Agrega `tramo.id_proyecto`.
- Crea `usuario_tramo` a partir de `usuario_frente`.
- Retira `frente` y `tramo_nucleo.id_frente`.
- Reconstruye vistas dependientes.

La 003 no usa `schema_migrations` y no es reejecutable. Se reconoce aplicada
cuando existen `proyecto` y `usuario_tramo`, y ya no existen `frente` ni
`usuario_frente`.

### 004 — Adaptaciones 2.0

Archivo:
`backend/db/migrations/004_adaptaciones_fase2.sql`

Requiere 003. Crea identidad normalizada, relaciones de titulares e
integrantes ORV, minutas, acuerdos, versiones documentales, pagos y alertas.
Registra la versión `004` en `schema_migrations` y rechaza una segunda
ejecución.

### 005 — Subcorte 2A

Archivo:
`backend/db/migrations/005_subcorte_2a_integridad_afectaciones.sql`

Requiere 004. Refuerza la integridad de afectaciones colectivas e
individuales:

- `colectivo` no puede tener `id_parcela`.
- `individual` debe tener `id_parcela`.
- La parcela individual debe estar activa, tener PPT, soporte o justificación
  registral y titulares activos suficientes.
- Una parcela en `copropiedad` requiere al menos dos titulares activos.
- PostgreSQL protege la baja o degradación de parcelas y titulares
  referenciados por afectaciones individuales activas.
- Registra la versión `005` en `schema_migrations` y rechaza una segunda
  ejecución.

La migración es expansiva y no corrige datos silenciosamente: si encuentra
afectaciones o parcelas incompatibles, aborta antes de cambiar el esquema.

### 006 — Subcorte 2B

Archivo:
`backend/db/migrations/006_subcorte_2b_secuencia_estados.sql`

Requiere 005. Es expansiva y transaccional: agrega la identidad
`afectacion_ciclo`, relaciones de linaje nulas para compatibilidad histórica,
salida terminal por afectación, vigencia financiera, restricciones y triggers
de secuencia/concurrencia, y vistas de estado por ciclo, afectación,
`tramo_nucleo` y dashboard. Crea únicamente una raíz estructural original por
afectación existente; no asocia actividades, asambleas, convenios o trámites
históricos por inferencia.

La 006 fue aplicada primero sobre copias temporales representativas y después,
el 3 de agosto de 2026, sobre la base de referencia del equipo que contenía
datos operativos. El despliegue activo se realizó con backend y scheduler
detenidos, `ON_ERROR_STOP=1`, transacción completa y respaldo previo validado.

No eliminar columnas heredadas hasta desplegar y validar el Corte principal 2.
La contracción de columnas heredadas de Adaptaciones 2.0 queda reservada para
una migración posterior.

### 007 — Subcorte 2C

Archivo:
`backend/db/migrations/007_subcorte_2c_navegacion_documental.sql`

Requiere 006. Es expansiva y transaccional: admite
`documentacion_soporte.entidad_relacionada_tipo = 'tramo_nucleo'`, actualiza el
trigger de validación de referencias documentales, agrega a `minuta` las
columnas nullable `id_afectacion` e `id_ciclo_afectacion`, y protege su
pertenencia mediante `CHECK`, FK compuesta e índice.

No reclasifica documentos históricos ni infiere minutas propias por fecha,
actividad o asunto. Las minutas existentes permanecen compartidas en
`tramo_nucleo` mientras no tengan relación explícita con una afectación/ciclo.

La 007 fue aplicada en este entorno local el 4 de agosto de 2026 con respaldo
previo y `ON_ERROR_STOP=1`. La base local de esta máquina registra ahora 004,
005, 006, 007, 008 y 009 en `schema_migrations`.

### 008 — Corte 4: autenticación formal

Archivo:
`backend/db/migrations/008_corte4_autenticacion_formal.sql`

Requiere 007. Es expansiva y transaccional: crea `sesion_usuario`,
`evento_acceso` y `estado_autenticacion_usuario`; protege eventos y sesiones
contra cambios o DELETE indebidos; correlaciona cada modificación del estado
de bloqueo con un evento de la misma transacción; revoca sesiones cuando un
usuario se da de baja; y redacta hashes de contraseña, sesión y CSRF en nuevas
fotografías de bitácora.

La 008 fue ensayada desde cero en bases aisladas y aplicada a `db_trenes` el 5
de agosto de 2026, con backend y scheduler detenidos, cero transacciones
concurrentes, `ON_ERROR_STOP=1` y respaldo validado
`backups/software-pa-db_trenes_pre_008_20260805.dump` con permisos `0600`.
No se infirieron sesiones ni bloqueos históricos; la cuenta existente recibió
contador cero y ninguna sesión.

### 009 — Corte 4: auditoría veraz de expiraciones

Archivo:
`backend/db/migrations/009_corte4_auditoria_sistema_sesion.sql`

Requiere 008. Sustituye de forma no destructiva `fn_audit_log()` para que una
expiración automática no se atribuya falsamente al usuario objetivo. La
excepción sólo se admite para una actualización de revocación correlacionada
con un evento `sesion_expirada` sin actor, de la misma sesión y transacción;
PostgreSQL rechaza cambios colaterales en cualquier otro campo de la sesión.

La 009 fue probada con la regresión completa en una base aislada y aplicada a
`db_trenes` el 5 de agosto de 2026, con escritores detenidos, cero
transacciones concurrentes, `ON_ERROR_STOP=1` y respaldo validado
`backups/software-pa-db_trenes_pre_009_20260805.dump` con permisos `0600`.

## 6. Trabajo realizado

### Corte principal 1 — Modelo territorial: terminado

Commit principal:

```text
d80983a feat: agregar tabla proyecto y eliminar tabla frente
```

Quedaron implementados Proyecto → Tramo, `usuario_tramo`, el retiro de Frente
y los ajustes de modelos, API, navegación, dashboard y datos iniciales.

### Adaptaciones 2.0 — trabajo adicional: A, B y C terminados

Commits:

```text
05919de feat: preparar adaptaciones estructurales fase 2
f6f7073 feat(backend): implementar adaptaciones fase 2
e65010d feat(frontend): integrar flujo operativo fase 2
```

Resultados principales:

- `persona`, `persona_nucleo`, `persona_fuente_legacy`.
- `orv_integrante` y `parcela_titular`.
- Operaciones atómicas de parcela con titular y ORV con integrantes.
- Minutas y acuerdos.
- Pagos de indemnización con límite económico protegido en PostgreSQL.
- Versiones documentales inmutables.
- Alertas no vistas y scheduler diario.
- Routers y servicios separados para evitar sobrecargar `main.py`.
- Selector de personas y módulos de ORV, minutas, pagos y documentos.
- Centro global de alertas.
- Mejoras de accesibilidad y división del bundle por rutas.

Validación técnica realizada:

```text
backend:  87 pruebas aprobadas
API:      0 combinaciones de ruta y método duplicadas
frontend: 0 errores y 0 advertencias de oxlint
build:    producción exitosa, sin chunks mayores a 500 kB
```

La validación se realizó también sobre una copia temporal exacta de la base,
que fue eliminada al terminar.

Limitación funcional descubierta durante esta actualización documental:

- `frontend/src/components/fase2/DocumentosPanel.jsx` intenta crear y listar
  documentos con `entidad_relacionada_tipo = 'tramo_nucleo'`.
- La restricción vigente de `documentacion_soporte` sólo admite
  `nucleo_agrario`, `afectacion`, `convenio` u `orv`.
- Por tanto, la creación desde ese panel falla en PostgreSQL y la consulta no
  representa un tipo válido del modelo.
- No se corrigió como parte de esta actualización de documentación. Debe
  resolverse en el Corte principal 2 vinculando el panel con la afectación
  abierta y agregando una prueba de integración frontend/API/base.

Las 87 pruebas siguen siendo el resultado técnico ejecutado, pero no cubrieron
este recorrido completo de la interfaz. No deben interpretarse como validación
funcional de usuario final.

Validación posterior de la captura de afectaciones confirmadas:

```text
backend:  89 pruebas aprobadas
frontend: 0 errores y 0 advertencias de oxlint
build:    producción exitosa
```

El alta de `afectacion` ahora exige geometría WKT y valida en PostGIS que sea
un polígono o multipolígono válido y no vacío. Los formularios colectivo e
individual capturan y envían esa geometría. Esta corrección no cambia la
limitación pendiente del panel documental descrita arriba.

Revalidación del repositorio realizada el 30 de julio de 2026:

```text
backend:  89 pruebas recopiladas; no se ejecutó la suite sin .env/base activa
API:      74 rutas y 0 combinaciones de método/path duplicadas
frontend: 0 errores y 0 advertencias de oxlint
build:    producción exitosa usando un directorio temporal
```

El build directo sobre `frontend/dist` no pudo sobrescribir algunos assets
propiedad del usuario `nobody`; no fue un error del código. La salida
alternativa en `/tmp` terminó correctamente y su chunk mayor fue de 289.34
kB. Esta revalidación no sustituye una ejecución completa contra PostgreSQL.

### Corte principal 2 — Subcorte 2B implementado y validado en copia aislada

El 3 de agosto de 2026 se implementaron:

- migración expansiva 006 con ciclos, terminalidad, linaje, vigencia
  financiera, bloqueo concurrente y vistas derivadas;
- estados separados operativo, registral, financiero y de liberación;
- cierre individual por indemnización completa y colectivo por indemnización
  más retiro de fondos completo del mismo ciclo;
- sustitución no acumulativa de montos por modificatorios;
- servicio y endpoints transaccionales de apertura/cierre;
- autorización por rol y `usuario_tramo` en recursos y agregados del flujo;
- panel mínimo para actividades, ciclos, terminalidad, FIFONAFE, retiro y
  consulta autoritativa del saldo;
- protección de rutas heredadas contra saltos y errores internos.

Validación ejecutada sobre `db_trenes_2b_test_final5`, copia lógica de la base
activa con 006 aplicada exclusivamente allí:

```text
backend:  104 pruebas aprobadas; 1 advertencia de deprecación de Starlette
datos:    0 afectaciones sin ciclo original y 0 ciclos huérfanos
vistas:   consultas de estado y dashboard ejecutadas correctamente
frontend: 0 errores de oxlint
build:    producción exitosa en /tmp; chunk mayor 289.34 kB
```

La base activa `db_trenes` fue migrada posteriormente a 006. La entrega aún no
incluye commit, push ni validación de aceptación con usuarios. Las copias
temporales se eliminaron después de conservar resultados y conteos en la
evaluación técnica.

Evidencia del despliegue activo:

```text
respaldo: backups/software-pa-db_trenes_pre_006_20260803.dump
tamaño:   418744 bytes
SHA-256:  85a9cece607d83330c6132870e61a55e89e311798e40ca3b95cbb4c7b5fc7757
restore:  restauración completa comprobada; recuperó 004/005 y 6/20 afectaciones
migración: BEGIN → COMMIT; versión 006 registrada
integridad: 0 raíces faltantes, 0 ciclos huérfanos, 0 vigencias duplicadas
servicios: backend y scheduler reanudados; raíz/OpenAPI HTTP 200
seguridad: endpoint de estado devuelve 401 sin token
```

## 7. Estado de la base local validada

El 28 de julio de 2026 la base activa local fue reiniciada de forma controlada.
Se conservaron:

- Un usuario administrador.
- 32 entidades federativas.
- 2,478 municipios.
- El proyecto Tren Maya.
- Siete tramos del Tren Maya con geometría.
- La asignación del administrador a los siete tramos.

No quedaron datos operativos de prueba. La base anterior se preservó
temporalmente como `db_trenes_pre_reinicio_20260728`.

Este estado sólo describe el entorno local validado. En otro equipo se debe
consultar el esquema real; `git pull` descarga los SQL, pero no modifica
volúmenes de PostgreSQL. Una base que sólo tiene 002 debe aplicar 003 y luego
004, con respaldo y verificación entre ambas.

La base activa local de esta máquina quedó verificada después de aplicar 009 el
5 de agosto de 2026:

```text
base/usuario:          db_trenes / alfredo
schema_migrations:     004, 005, 006, 007, 008, 009
afectaciones:          0 activas / 0 totales
convenios:             0 activos / 0 totales
FIFONAFE/pagos activos: 0 / 0
afectacion_ciclo:      0 ciclos activos / 0 totales
integridad 2B:         sin datos operativos locales que conciliar
integridad 2C:         columnas de minuta y tipo documental tramo_nucleo verificados
autenticación:         1 estado / 0 sesiones / 0 eventos iniciales
auditoría sensible:    0 filas con contrasena_hash, token_hash o csrf_hash
vistas activas:        afectación, tramo_nucleo y dashboard consultables
```

El archivo `.env` local ya permite conectarse al servicio `db`. Estos valores
describen sólo este entorno; en cada equipo se debe verificar el esquema real.
En otros equipos, `git pull` descarga las migraciones, pero no las aplica al
volumen PostgreSQL; cada colaborador debe verificar `schema_migrations` y
respaldar antes de ejecutar 006, 007, 008 o 009.

## 8. Plan principal vigente de cinco cortes

### Corte 1 — Modelo territorial: terminado

Proyecto + Tramo + Tramo_Núcleo sin Frente + `usuario_tramo`.

### Corte 2 — Expediente maestro y subexpedientes por afectación: implementado técnicamente

Decisión aprobada:

```text
tramo_nucleo = expediente maestro territorial de liberación
afectacion   = subexpediente operativo confirmado
```

Situación actual:

- `/expedientes` lista `tramo_nucleo`.
- `/expedientes/:id_tramo_nucleo` abre el expediente maestro y conserva las
  actuaciones compartidas.
- `/expedientes/:id_tramo_nucleo/afectaciones/:id_afectacion` abre el
  subexpediente operativo de la afectación seleccionada.
- Asambleas, convenios, FIFONAFE, pagos, minutas y documentos tienen filtros
  backend por `id_afectacion` y, cuando aplica, por `id_ciclo_afectacion`.
- `documentacion_soporte` admite documentos maestros de `tramo_nucleo` y
  documentos propios de `afectacion`.
- Las salidas terminales y el estado de liberación por pago fueron resueltos en
  2B; el subexpediente 2C consume ese estado autoritativo.
- Está pendiente la validación funcional y de experiencia con usuarios finales
  sobre el recorrido completo de 2C.

Resultado esperado:

```text
Proyecto
└── Tramo
    └── Tramo_Núcleo
        ├── Expediente maestro /expedientes/:id_tramo_nucleo
        └── Afectación confirmada
            └── Subexpediente
                /expedientes/:id_tramo_nucleo/afectaciones/:id_afectacion
                ├── antecedentes de sensibilización
                ├── antecedentes de caminamiento y análisis
                ├── monto, observaciones y soporte de BDT, cuando aplique
                ├── actuaciones y minutas posteriores
                ├── asamblea, solamente cuando corresponda
                ├── convenio
                ├── RAN
                ├── FIFONAFE y pago
                ├── documentos
                └── cierre
```

La sensibilización sigue siendo una etapa explícita previa al caminamiento.
El caminamiento delimita superficie y geometría e identifica bienes distintos
a la tierra. No se crea una afectación preliminar; al registrar la afectación
confirmada, las etapas compartidas permanecen en el expediente maestro y
quedan accesibles desde el subexpediente como antecedentes. El alcance actual
sólo conserva `convenio.monto_bdt`, observaciones y documentos de soporte; no
incluye diseñar un inventario detallado ni un proceso de avalúo.

Reglas que guiaron el Corte 2 y deben conservarse:

1. Auditar qué entidades son propias de una afectación y cuáles son
   compartidas.
2. Mantener ORV en el nivel del núcleo; no duplicarla por afectación.
3. Mantener transiciones compatibles y migraciones expansivas para cambios
   posteriores.
4. Mantener el expediente maestro y el detalle operativo por `id_afectacion`.
5. Conservar la navegación para abrir afectaciones dentro de su
   `tramo_nucleo`, sin eliminar la vista maestra.
6. Mostrar sólo las etapas aplicables al tipo colectivo o individual.
7. Hacer cumplir la secuencia obligatoria con las entidades existentes y
   calcular avance legal, geoespacial y financiero por afectación.
8. Migrar o vincular datos existentes sin inferir relaciones ambiguas.
9. Añadir pruebas de aislamiento: datos de una afectación no deben aparecer
   en otra del mismo `tramo_nucleo`.
10. Conservar documentos maestros como
    `entidad_relacionada_tipo = 'tramo_nucleo'` y documentos propios como
    `entidad_relacionada_tipo = 'afectacion'`.
11. Representar por afectación las salidas terminales de expropiación directa
    y comunidad indígena cuando no correspondan a todo el núcleo.
12. Derivar `liberado` sólo después del pago y mostrar estados mixtos en el
    expediente maestro sin ocultar afectaciones terminales.

No comenzar eliminando `tramo_nucleo` ni trasladando ciegamente todas las FK a
`afectacion`.

#### Subcorte 2A terminado — Reforzar afectación colectiva e individual

Este fue el primer trabajo aprobado dentro del Corte principal 2. Su propósito
fue cerrar la ambigüedad sin confundir derechos colectivos con una parcela en
copropiedad:

```text
afectación colectiva
  = derechos del núcleo agrario
  = no usa una parcela normalizada

afectación individual
  = derechos parcelarios
  = requiere una parcela
  = la parcela puede ser individual o estar en copropiedad
```

Regla de integridad objetivo:

```sql
CHECK (
    (tipo_afectacion = 'colectivo' AND id_parcela IS NULL)
    OR
    (tipo_afectacion = 'individual' AND id_parcela IS NOT NULL)
)
```

Alcance aprobado:

1. Sustituir `chk_individual_requiere_parcela` por una restricción
   bidireccional que también prohíba parcela en la afectación colectiva.
2. Mantener la FK compuesta que garantiza que la parcela individual y el
   `tramo_nucleo` pertenecen al mismo núcleo.
3. Fortalecer la validación de la parcela individual: debe estar activa,
   tener número PPT, soporte o justificación registral y titulares activos.
4. Exigir al menos dos titulares activos para usar una parcela marcada como
   `copropiedad` en una afectación. La operación compuesta debe ejecutarse en
   una sola transacción.
5. Impedir que se inactive la parcela o su último titular mientras exista una
   afectación individual activa.
6. Separar los contratos de entrada del backend en colectivo e individual,
   discriminados por `tipo_afectacion`; el contrato colectivo no debe exponer
   `id_parcela`.
7. Retirar del formulario colectivo los subtipos `individual` y
   `copropiedad`, que pertenecen a `parcela.tipo_parcela`.
8. Permitir que el formulario individual capture una parcela en copropiedad
   con varios titulares antes de crear la afectación.
9. No duplicar `parcela.no_parcela_ppt` en la afectación individual.
   `afectacion.no_parcela_solar` se conserva temporalmente como referencia
   textual de las matrices colectivas hasta definir un nombre menos ambiguo.
10. Agregar pruebas de API y de PostgreSQL para todas las combinaciones
    válidas e inválidas.

La migración ejecuta primero una prevalidación y aborta si encuentra
colectivas con parcela o individuales sin parcela. No reclasifica ni corrige
filas silenciosamente. Aunque la base local no contiene expedientes
operativos, la migración fue diseñada para ser segura en otros entornos.

Este subcorte no incluye todavía padrón nominal, participantes de asamblea,
firmantes de convenio ni rediseño registral; son decisiones separadas.

Diagnóstico histórico observado antes de iniciar el Subcorte 2A:

- La restricción actual sólo exige parcela a la afectación individual; aún no
  prohíbe parcela en una colectiva.
- La FK compuesta de pertenencia al mismo núcleo ya existe.
- La validación PostgreSQL de parcela es parcial: verifica PPT, titular activo
  y soporte o justificación registral, pero no cubre toda la regla objetivo.
- La protección del último titular existe en el servicio, no como protección
  completa ante escrituras directas en PostgreSQL.
- El backend mantiene un único contrato de alta de afectación.
- El formulario colectivo todavía expone subtipos individuales y de
  copropiedad.
- El formulario individual todavía captura un solo titular.
- No están implementadas la validación mínima de dos copropietarios, la
  restricción bidireccional, la separación de contratos ni toda su matriz de
  pruebas.

Estado de implementación en la rama `feature/backend-logica` (2026-07-31):

- Se preparó la migración expansiva `005_subcorte_2a_integridad_afectaciones.sql`.
  Su prevalidación y sintaxis se comprobaron primero dentro de una transacción
  que terminó en `ROLLBACK`; posteriormente se aplicó correctamente. La base
  activa está en versión `005`.
- Se implementaron contratos y rutas separados para afectaciones colectivas e
  individuales, incluida la creación atómica de parcela, titulares y
  afectación individual nueva.
- Se actualizaron los formularios: el colectivo ya no ofrece subtipos
  individuales ni copropiedad; el individual no duplica el PPT y permite
  capturar copropietarios.
- Se agregaron pruebas de contratos y atomicidad. La suite completa de backend
  pasó con `95 passed` sobre el esquema con 005 aplicada.

#### Subcorte 2B implementado — Secuencia, excepciones y estado

La rama contiene la migración 006, backend, frontend y pruebas descritos en la
sección 6. La implementación enlaza etapas, modela ciclos repetibles, incorpora
salidas terminales, separa progreso registral/financiero/liberación y deriva
el cierre con las reglas aprobadas para derechos colectivos e individuales.

Estado de entrega:

1. Código y migración: implementados.
2. Suite backend, lint y build: aprobados en copia aislada.
3. Base activa: 006 aplicada y verificada con respaldo previo.
4. Aceptación funcional con usuarios: completada y aprobada.
5. Commit y push: realizados.

#### Subcorte 2C implementado — Navegación y aislamiento documental

El 4 de agosto de 2026 se implementó técnicamente:

1. Mantener el expediente maestro de `tramo_nucleo`.
2. Abrir cada afectación en su propio subexpediente mediante
   `/expedientes/:id_tramo_nucleo/afectaciones/:id_afectacion`.
3. Mostrar antecedentes compartidos sin duplicarlos.
4. Aislar asambleas, convenios, trámites FIFONAFE, pagos, minutas y documentos
   propios de cada afectación.
5. Corregir el tipo de relación documental de expediente maestro admitiendo
   `entidad_relacionada_tipo = 'tramo_nucleo'` en PostgreSQL y backend.
6. Agregar autorización territorial para relaciones documentales dinámicas y
   minutas.

Validación técnica ejecutada:

```text
respaldo: backups/pre_migracion_007_20260804.dump
tamaño:   288K
SHA-256:  2573a276dea8603cc82c519e56f95a92df3a9708b389b63ed53cdf51a8f7e014
migración: BEGIN → COMMIT; versión 007 registrada
backend:  107 pruebas aprobadas; 1 advertencia de deprecación de Starlette
frontend: npx oxlint src sin advertencias ni errores
build:    producción exitosa en directorio temporal
```

La base local usada para esta validación no contiene expedientes operativos; las
pruebas 2C crean sus fixtures y verifican aislamiento entre afectaciones del
mismo `tramo_nucleo`. En ambientes con datos reales se debe respaldar y ejecutar
preflight antes de aplicar 007.

Estado de aceptación funcional:

1. Validación funcional con usuarios finales: completada y aprobada según
   continuidad de trabajo del 4 de agosto de 2026.
2. Commit y push: pendiente de confirmación en el cierre de cambios.

### Corte 3 — Seguridad inmediata: 3A de repositorio implementado

El 4 de agosto de 2026 se implementó el hardening de repositorio del Corte 3:

- `backend/app/auth.py` rechaza `SECRET_KEY` ausente, placeholder o demasiado
  corta antes de arrancar.
- `backend/scripts/create_admin.py` ya no contiene credenciales fijas; lee
  configuración desde variables de entorno o prompt interactivo, valida datos
  mínimos, usa fecha con zona y rehabilita triggers si usa la ruta especial del
  primer usuario.
- `backend/db/seed.sql` ya no crea un usuario administrador con credenciales
  conocidas; exige un administrador activo previo para establecer auditoría.
- `.env.example`, `README.md` y `docs/migraciones.md` documentan bootstrap y
  rotación sin copiar secretos.
- Las pruebas de autenticación pueden usar `TEST_ADMIN_EMAIL` y
  `TEST_ADMIN_PASSWORD` por ambiente.

Validación ejecutada:

```text
esquema:  schema_migrations registra 004, 005, 006, 007, 008 y 009
backend:  117 pruebas aprobadas; 1 advertencia de deprecación de Starlette
frontend: npx oxlint src sin errores
bootstrap: ejecución no interactiva sin ADMIN_PASSWORD falla cerrado
diff:     git diff --check sin errores
secretos: búsqueda enfocada sin credenciales conocidas en archivos operativos tocados
```

La rotación local de `SECRET_KEY`, contraseña del rol PostgreSQL y PgAdmin fue
reportada como realizada por el responsable antes del trabajo del 5 de agosto
de 2026. Este hecho no demuestra la rotación en otros ambientes ni autoriza a
registrar valores; cada ambiente mantiene custodia externa.

### Corte 3 — Seguridad inmediata: parcial

Ya realizado:

- Handler global sin fuga de `str(exc)`.
- Registro interno de excepciones.
- Escape de valores en popups de `Mapa.jsx` para mitigar XSS.
- `docker-compose.yml` consume variables obligatorias del entorno.
- Existe `.env.example` sin secretos reales y `.env` está ignorado por Git.
- Bootstrap seguro de administrador sin credenciales fijas en
  `scripts/create_admin.py`.
- `seed.sql` separado de credenciales operativas.
- Validación de `SECRET_KEY` contra placeholders y longitud insuficiente.
- Documentación de bootstrap y rotación por ambiente.

Pendiente:

- Replicar y verificar la rotación en cada ambiente distinto del local, con
  custodia externa y evidencia sin valores sensibles.
- Verificar recuperación y revocación de credenciales anteriores por ambiente.

No copiar las credenciales actuales a documentación nueva.

### Corte 4 — Autenticación formal: incremento principal implementado

Implementado y validado técnicamente el 5 de agosto de 2026:

- El frontend ya no usa `localStorage` para token ni usuario; restaura la
  identidad desde `GET /api/auth/sesion`.
- Cookie de sesión opaca HttpOnly; producción exige `Secure`; cookie CSRF
  separada, header `X-CSRF-Token` y validación exacta de `Origin`.
- Sesiones con hash SHA-256 en PostgreSQL, revocación, logout actual/total y
  revocación administrativa sin DELETE físico.
- Registro append-only de login exitoso/fallido, bloqueo, expiración, logout,
  revocación y desbloqueo; identidad inexistente no guarda correo ni hash
  enumerable.
- La expiración automática queda como evento sin actor humano; PostgreSQL
  impide atribuirla a la víctima y rechaza modificaciones colaterales de la
  sesión aunque exista un evento correlacionado.
- Cinco fallos consecutivos bloquean 15 minutos con lock de fila; existe
  desbloqueo admin y recuperación operativa auditable del único admin.
- Inactividad servidor de 30 minutos y límite absoluto de 8 horas.
- Baja lógica de usuario revoca sus sesiones en la misma transacción.
- Política mínima de 12 caracteres, mayúscula, minúscula, número y símbolo en
  `UsuarioCreate`, alineada con bootstrap.
- 117 pruebas backend pasan en base aislada, incluido quinto fallo concurrente,
  CSRF, expiraciones, integridad DB y redacción. Oxlint y build frontend pasan.

Pendiente antes de declarar Corte 4 terminado:

- Inventariar consumidores externos y retirar el login bearer/JWT heredado.
- Validar cookie `Secure`, host/origen y proxy confiable detrás del TLS real.
- Ejecutar aceptación funcional E2E en navegadores soportados.

### Corte 5 — Importación y reportes: pendiente

- Endurecer el importador GeoJSON.
- Limitar tamaño y validar `FeatureCollection`.
- Validar tipo de geometría por entidad.
- Reportar errores por feature.
- Evitar `flush()` antes de establecer una geometría obligatoria.
- Alinear importación con Proyecto → Tramo.
- Dashboard y reportes por proyecto.
- Indicadores por afectación y agregados por tramo/proyecto.

#### Componente aprobado — Derecho de vía versionado

El Corte 5 debe sustituir gradualmente el cálculo implícito basado únicamente
en `tramo.geometria_linea` y `tramo.ancho_total_derecho_via_m` por una franja
oficial versionada. El nombre propuesto para la nueva entidad es
`franja_derecho_via`.

Modelo mínimo:

```text
franja_derecho_via
├── id_franja
├── id_tramo
├── version
├── ancho_izquierdo_m
├── ancho_derecho_m
├── geometria_poligono
├── fuente
├── fecha_vigencia_inicio
├── fecha_vigencia_fin
├── activo
└── ciclo de vida y auditoría
```

Reglas objetivo:

1. Cada versión pertenece a un tramo y conserva la fuente oficial que la
   originó.
2. La geometría debe ser Polygon o MultiPolygon válido con SRID 4326.
3. Los anchos deben ser positivos cuando se proporcionen.
4. No puede haber más de una versión activa para el mismo tramo.
5. Las fechas de vigencia no pueden invertirse.
6. Las afectaciones confirmadas deben intersectar la franja activa; una vez
   completada la transición no se validarán contra un búfer implícito.
7. Las versiones anteriores no se sobrescriben ni eliminan: se desactivan con
   trazabilidad.
8. El importador GeoJSON debe validar la entidad, geometría, versión, fuente y
   tramo antes de insertar.

La transición será de expansión:

```text
crear franja versionada
→ generar o importar versión inicial desde los datos vigentes
→ comparar contra el búfer actual
→ desplegar backend y frontend
→ cambiar la validación espacial de afectación
→ retirar el uso operativo del ancho simple sólo después de validar
```

`tramo.ancho_total_derecho_via_m` y el comportamiento actual no deben
eliminarse en la primera migración. Servirán como compatibilidad y fuente para
la versión inicial hasta comprobar que todos los tramos cuentan con una
franja válida.

## 9. Trabajo técnico transversal pendiente

- Conservar y probar periódicamente la restauración del respaldo previo a 006
  ubicado en `backups/software-pa-db_trenes_pre_006_20260803.dump`.
- Conservar el respaldo previo a 007 de este entorno local:
  `backups/pre_migracion_007_20260804.dump`.
- Replicar 007 en otros ambientes sólo después de respaldo, verificación de
  `schema_migrations` y preflight de tipos documentales.
- Conciliar manualmente relaciones históricas 2B que permanecen nulas; no
  inferirlas por fecha, expediente o cercanía de registros.
- ~~Ejecutar aceptación funcional con usuarios sobre rutas colectiva,
  individual, terminal, modificatorio y expediente mixto.~~ (Completada)
- ~~Ejecutar validación funcional y de experiencia con usuarios finales sobre
  el Subcorte 2C.~~ (Completada y aprobada según continuidad del 4 de agosto
  de 2026)
- Decidir si una base limpia necesita conservar
  `persona_fuente_legacy`; hoy es trazabilidad de migración, no una segunda
  identidad maestra.
- Conciliar identidades únicamente si aparecen datos reales heredados.
- Retirar columnas legacy de ORV, parcela y documentos después del nuevo
  flujo y de verificaciones de uso.
- Consolidar posteriormente `001_init_schema.sql` para instalaciones nuevas.
- Rotar secretos ya expuestos en historial en cada ambiente; el hardening de
  repositorio del Corte 3 ya está implementado, pero no sustituye la rotación
  operativa.

## 10. Instrucción para continuar

La siguiente tarea no es crear Proyecto, repetir Adaptaciones 2.0, rediseñar
2A ni reimplementar 2B.

Próximo paso operativo:

1. Validar Corte 4 detrás del TLS real: cookie `Secure`, origen público exacto
   y, si se requiere IP cliente, proxies confiables configurados por IP exacta.
2. Inventariar consumidores del bearer heredado; migrarlos a cookie y aprobar
   la fecha de contracción antes de dejar de emitir/aceptar JWT.
3. Ejecutar aceptación E2E de login, quinto fallo, desbloqueo, expiración,
   logout y RBAC/territorio en navegadores soportados.
4. Replicar 008 y luego 009 en otros ambientes sólo después de respaldo,
   verificación individual de 004/005/006/007 y preflight de bitácora sensible.
5. Revisar y confirmar el diff antes de commit/push; no declarar Corte 4
   terminado mientras bearer siga habilitado.
El derecho de vía versionado está aprobado como componente futuro del Corte
5. No debe mezclarse en el Subcorte 2C.
