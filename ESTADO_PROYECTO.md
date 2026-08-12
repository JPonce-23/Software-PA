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

**Última actualización:** 12 de agosto de 2026

**Rama de trabajo:** `feature/backend-logica`

**Trabajo funcional actual:** la Administración territorial y de accesos quedó
implementada y validada. El ambiente aislado `software_pa_uat` está preparado
con 015, fixture reproducible y cuatro roles; backend y scheduler locales están
conectados actualmente a UAT para iniciar el recorrido real desde el frontend.
La base original `db_trenes` también quedó alineada con 015 después de respaldo
verificado y baja lógica de sus dos franjas de prueba incompatibles, con actor,
fecha, fin de vigencia y motivo. El siguiente trabajo es la aceptación manual
del flujo completo por rol. El Corte 4 permanece con contracción local
validada y aceptación operativa TLS/E2E diferida; ese gate no bloquea este
incremento local, pero sí bloquea liberar autenticación a operación.

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
backend/db/migrations/010_*.sql         Franja de derecho de vía versionada
backend/db/migrations/011_*.sql         Cierre financiero con pago suficiente
backend/db/migrations/012_*.sql         Regularización correctiva del Corte 5
backend/db/migrations/013_*.sql         Auditoría de integridad temporal de franjas
backend/db/migrations/014_*.sql         Auditoría de geometrías de núcleos
backend/db/migrations/015_*.sql         Integridad de administración territorial
backend/tests/                          regresión e integración
backend/app/routers/authentication.py   endpoints de sesión y revocación
backend/app/services/authentication.py  reglas transaccionales de autenticación
backend/app/routers/administration.py   contratos administrativos reservados
backend/app/services/administration.py  asignaciones y bajas compuestas
docs/evaluaciones/2026-08-06-corte-4-contraccion-bearer-auditoria-final.md
                                        cierre local de auditoría de contracción
docs/validacion-tls-e2e-corte-4.md      checklist operativo TLS/E2E externo
backend/app/routers/flujo.py            transiciones explícitas de 2B
backend/app/services/flujo.py           dominio transaccional de 2B
backend/app/services/access.py          autorización territorial
frontend/src/pages/ExpedienteDetail.jsx expediente actual por tramo_nucleo
frontend/src/pages/AfectacionSubexpediente.jsx subexpediente por afectacion
frontend/src/pages/ExpedientesList.jsx  listado actual de tramo_nucleo
frontend/src/pages/AdministracionTerritorial.jsx configuración territorial
frontend/src/pages/AdministracionUsuarios.jsx usuarios y accesos
frontend/src/components/fase2/          módulos agregados en Adaptaciones 2.0
frontend/src/components/fase2/FlujoLiberacionPanel.jsx flujo mínimo de 2B
backend/scripts/seed_uat.py              fixture reproducible para UAT aislado
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

### 010 — Corte 5: franja de derecho de vía versionada

Archivo:
`backend/db/migrations/010_corte5_franja_derecho_via.sql`

Es expansiva y transaccional. Crea la franja oficial versionada por tramo,
conserva el ancho heredado como compatibilidad y registra 010 al final.

### 011 — Cierre financiero con pago suficiente

Archivo:
`backend/db/migrations/011_pago_suficiente.sql`

Requiere 010. Protege el cierre de indemnización sin pago suficiente, impide
reducir pagos que sostienen un trámite completo y actualiza el cálculo de
`vw_afectacion_ciclo_estado` sin reducir los contratos de las vistas
superiores.

El 10 de agosto de 2026 se detectó una ejecución local parcial previa: las
funciones y el trigger existían, pero 011 no estaba registrada porque el SQL
intentaba eliminar vistas con dependencias. La migración fue corregida con
transacción exterior, bloqueo asesor, guardas 010/011, preflight y reemplazo
no destructivo de la única vista afectada. Se validó primero sobre esquema
aislado y después sobre una restauración completa del respaldo
`backups/pre_011_auth_recovery_restorable_20260810.dump`, con permisos `0600`.
La repetición fue rechazada por la guarda y la base activa registró 011 con
`COMMIT` y escritores detenidos.

### 012 — Regularización correctiva del Corte 5

Archivo:
`backend/db/migrations/012_regularizacion_corte5.sql`

Requiere 010 y 011. Agrega guardas, bloqueo asesor, preflight, restricciones
de versión y geometría, FK de actores, auditoría, baja lógica y protección
contra `DELETE` físico para `franja_derecho_via`. Completa la versión inicial
sólo cuando el tramo activo no tiene historial y sus datos heredados permiten
una derivación inequívoca. Sustituye en PostgreSQL la validación espacial por
la franja activa y hace inmutables los datos sustantivos de cada versión.

Se ensayó sobre una copia lógica de la base activa, donde creó siete franjas y
rechazó la repetición. Después se aplicó a la base activa el 11 de agosto de
2026 con backend y scheduler detenidos, cero escritores, `ON_ERROR_STOP=1` y
respaldo validado
`backups/pre_012_corte5_regularizacion_20260811.dump`, de 544183 bytes,
permisos `0600` y SHA-256
`2eb2a454e006b64144038481c6e1ed4f8e7dcc2e53dd32315b569faf4355c93a`.

### 013 — Auditoría de integridad temporal de franjas

Archivo:
`backend/db/migrations/013_auditoria_integridad_franja.sql`

Requiere 012. La auditoría independiente comprobó que PostgreSQL todavía
aceptaba una fuente vacía y una versión cuya vigencia iniciaba antes que la
versión anterior. La migración agrega el `CHECK` de fuente no vacía y reemplaza
el trigger de versión para validar también el orden cronológico bajo el mismo
bloqueo asesor por tramo. Es expansiva, transaccional y aborta ante datos
preexistentes incompatibles; no reescribe versiones ni elimina estructuras.

Se ensayó en la restauración aislada
`audit_c5_013_20260811_2038`, rechazó la repetición y superó la suite completa
de 125 pruebas. Después se aplicó a la base activa el 11 de agosto de 2026 con
backend y scheduler detenidos, cero escritores y `ON_ERROR_STOP=1`. El respaldo
previo `backups/pre_013_corte5_auditoria_20260811.dump` tiene 1161975 bytes,
permisos `0600`, catálogo legible por `pg_restore -l` y SHA-256
`df505e946e0ed0834c7ddc93acb822290f34a66d4a26a29d00b1e1877fcd1582`.

### 014 — Auditoría de integridad geométrica de núcleos

Archivo:
`backend/db/migrations/014_auditoria_integridad_nucleo.sql`

Requiere 013. La auditoría confirmó que el importador validaba topología en el
servicio, pero la tabla permitía una geometría no vacía e inválida mediante una
escritura directa. La migración agrega un `CHECK` compatible con geometrías
históricas nulas y exige que toda geometría presente sea `MULTIPOLYGON` WGS84,
no vacía y válida. El preflight de la base activa encontró cero incompatibles.

Se ensayó y repitió la suite de 125 pruebas en la restauración aislada antes de
aplicarla a la base activa, donde después volvió a pasar la suite completa.
Backend y scheduler estuvieron detenidos y se confirmaron cero escritores.
El respaldo `backups/pre_014_corte5_nucleos_20260811.dump` tiene 1166829 bytes,
permisos `0600`, catálogo legible y SHA-256
`ad8d3855a1ac9b47c740f8d4b19f7a28398f163df5dd578daa9d396ab1889014`.

### 015 — Integridad de administración territorial

Archivo:
`backend/db/migrations/015_administracion_territorial.sql`

Requiere 014. Es expansiva y transaccional: agrega unicidad normalizada del
correo, restricciones geométricas y triggers para impedir hijos activos con
padres inactivos, asociaciones espaciales incoherentes, bajas de padres con
dependencias activas y la baja o degradación del último administrador activo.
Las transiciones sensibles usan bloqueos de fila o asesores para contemplar
concurrencia. No elimina ni reescribe estructuras existentes.

Se validó el 12 de agosto de 2026 en bases desechables. El primer ensayo sobre
una copia de la base activa abortó completo y sin cambios al encontrar dos
franjas activas vinculadas a tramos inactivos. Después de preparar otra copia
aislada, la migración y la suite de 131 pruebas pasaron.

La base `db_trenes` se alineó posteriormente el 12 de agosto de 2026: se generó
el respaldo `backups/db_trenes_pre_015_20260812.dump`, de 1231401 bytes,
permisos `0600`, catálogo legible por `pg_restore -l` y SHA-256
`17f7f260fb163bc5b84147cb97ac50a185eeb736af6cdb119d02a64af9bb9b21`.
Con escritores detenidos y `ON_ERROR_STOP=1`, se dieron de baja lógica las
franjas de prueba `id_franja` 19 y 41, con actor, fecha, fin de vigencia y
motivo, y luego se aplicó 015 con `COMMIT`. La validación posterior confirmó
`schema_migrations=015`, cero franjas activas bajo tramos inactivos, 11 triggers
015, el índice de correo normalizado, los 2 `CHECK` geométricos y rechazo
PostgreSQL de una franja activa con tramo inactivo mediante
`ADM_PADRE_INACTIVO`.

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

La base activa local de esta máquina se volvió a inspeccionar y alinear el 12
de agosto de 2026:

```text
base/rol:              db_trenes / pa_app
schema_migrations:     004, 005, 006, 007, 008, 009, 010, 011, 012, 013, 014, 015
datos operativos:      fixtures locales de prueba; no representan producción
integridad FK:         cero relaciones huérfanas después de la regresión
autenticación:         un estado por usuario; cero usuarios sin estado
recuperación F-01A:    fila del usuario 1 restaurada desde respaldo y evento
                       desbloqueo_recuperacion sin actor, misma transacción
vistas activas:        ciclo, afectación, tramo_nucleo y dashboard consultables
franjas:               cero franjas activas ligadas a tramos inactivos; las
                       franjas de prueba 19 y 41 quedaron con baja lógica
respaldo:              respaldos previos a 013, 014 y 015 validados con
                       pg_restore -l
backend:               131 pruebas aprobadas sobre base desechable con 015;
                       1 warning deprecado de Starlette
frontend:              build y lint aprobados; 2 recorridos Playwright de
                       administración aprobados en escritorio y móvil
```

El archivo `.env` local ya permite conectarse al servicio `db`. Estos valores
describen sólo este entorno; en cada equipo se debe verificar el esquema real.
En otros equipos, `git pull` descarga las migraciones, pero no las aplica al
volumen PostgreSQL; cada colaborador debe verificar `schema_migrations` y
respaldar antes de ejecutar 006, 007, 008, 009, 010, 011, 012, 013, 014 o 015.

Ambiente UAT preparado el 12 de agosto de 2026:

```text
base:                   software_pa_uat
schema_migrations:      004–015
escenario:              1 proyecto, 2 tramos, 2 franjas activas,
                        2 núcleos, 2 tramo_nucleo y 1 parcela
usuarios:               admin, geografo, operador y visualizador
territorio:             UAT-A asignado; UAT-B reservado para acceso denegado
servicios conectados:   backend y alertas_scheduler con APP_ENV=test
frontend:               http://localhost:5173
credenciales locales:   backups/uat_credentials.env, ignorado por Git, modo 0600
validación:              login de 4 roles; no-admin 403 en administración;
                        geografo sólo ve UAT-A y recibe 403 directo sobre UAT-B;
                        Playwright escritorio/móvil 2 aprobadas
```

El archivo de credenciales contiene únicamente usuarios sintéticos. No debe
confirmarse, copiarse a producción ni reutilizarse fuera de este UAT. Si Compose
recrea los servicios con el `.env` normal, reconectar UAT explícitamente con:

```bash
DB_NAME=software_pa_uat APP_ENV=test docker compose up -d --no-deps \
  --force-recreate backend alertas_scheduler
```

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

Contracción local aplicada y validada el 6 de agosto de 2026:

- El endpoint legacy `POST /api/auth/login`, la aceptación
  `Authorization: Bearer`, la emisión/validación JWT, los schemas `Token` y
  `TokenData`, los tests legacy y la dependencia `python-jose` fueron retirados
  del código local.
- La suite de pruebas usa sesiones cookie con CSRF mediante `admin_session` y
  credenciales inyectadas por `TEST_ADMIN_EMAIL` y `TEST_ADMIN_PASSWORD`.
- `docker-compose.yml` permite inyectar esas variables al contenedor backend
  sin persistir secretos, y `.env.example` documenta los nombres vacíos.
- Validación local ejecutada: Compose saludable, `schema_migrations` con 004,
  005, 006, 007, 008, 009, 010 y 011, backend sin `python-jose`, un estado de
  autenticación por usuario y suite backend completa con
  `119 passed, 1 warning`.
- El 10 de agosto de 2026 se recuperó de forma atómica el estado faltante del
  administrador local desde un respaldo que conservaba contador cero, sin
  bloqueo y su último acceso. La misma transacción registró
  `desbloqueo_recuperacion`; no se modificaron contraseña, rol ni territorios.
- Se creó una cuenta administradora no productiva mediante el bootstrap seguro
  para alinear `TEST_ADMIN_EMAIL`/`TEST_ADMIN_PASSWORD`; no registrar sus
  valores.

Pendiente antes de declarar Corte 4 terminado:

- Validar cookie `Secure`, host/origen HTTPS exacto y proxy confiable detrás del
  TLS real del ambiente de aceptación.
- Ejecutar aceptación funcional E2E en navegadores soportados.

Estos pendientes son un gate de aceptación/preliberación. No deben reportarse
como bloqueo de entorno para continuar el desarrollo local de otros incrementos,
salvo que la tarea solicitada sea cerrar Corte 4, validar operación real o
liberar autenticación en un ambiente de uso.

### Corte 5 — Importación y reportes: Terminado

Regularización correctiva aprobada e implementada el 11 de agosto de 2026:

- Se priorizó corregir el Corte 5 antes de agregar una capacidad nueva.
- La importación de núcleos es global para `admin`. El `geografo` puede elegir
  uno, varios o todos sus tramos asignados activamente; el backend vuelve a
  verificar cada asignación e intersección y aborta el lote completo ante un
  tramo no autorizado.
- La importación no crea ni infiere relaciones `tramo_nucleo`.
- El resumen de reportes respeta el alcance territorial.
- Las franjas fallan cerrado cuando no existe versión activa, serializan el
  versionado concurrente y conservan historial inmutable y auditado.
- PostgreSQL protege versión, geometría, unicidad activa, ciclo de vida,
  orden cronológico, fuente no vacía, auditoría, baja lógica, ausencia de
  `DELETE` y la intersección de afectaciones con la franja activa.
- La auditoría independiente corrigió el `500` de una raíz JSON no-objeto,
  exige territorio también para actualizar o dar de baja un núcleo y revoca
  las sesiones creadas por las regresiones concurrentes.
- Las pruebas de login y Corte 5 hacen logout explícito; quedaron cero sesiones
  `testclient` activas después de la suite completa.
- PostgreSQL rechaza ahora geometrías de núcleo presentes que estén vacías,
  sean topológicamente inválidas o no sean `MULTIPOLYGON` WGS84.
- La interfaz ofrece selección múltiple y “Todos mis tramos” al geógrafo,
  modo global al administrador, historial de franjas y rechazo de
  `FeatureCollection` para una franja.
- Validación: migraciones 012/013/014 aisladas y activas, repetición rechazada,
  `125 passed` en restauración aislada y también sobre la base activa;
  frontend con lint limpio y build de producción exitoso.

#### Componente aprobado e implementado — Dashboard Analítico y Uploader Masivo

- **Dashboard y reportes por proyecto**: Se habilitó la vista métrica general filtrable por `Proyecto`.
- **Endurecimiento del importador GeoJSON**: Se implementó el servicio masivo `POST /api/nucleos/importacion-masiva` protegiendo límite de memoria (10MB), procesando dinámicamente archivos GeoJSON iterando features en el backend sin uso de `flush` prematuro, reportando la lista exacta de errores por feature y permitiendo herencia global del `Municipio`.

#### Componente aprobado e implementado — Derecho de vía versionado

El Corte 5 implementó gradualmente la franja de derecho de vía oficial versionada (`franja_derecho_via`):

1. **Migraciones 010 y 012 aplicadas:** 010 creó la estructura versionada. La
   verificación posterior detectó que la base activa no tenía las versiones
   iniciales documentadas; 012 completó siete versiones de forma auditable y
   reforzó la integridad sin retirar el ancho heredado.
2. **Modelos y validaciones espaciales:** Se actualizaron `models.py` y `schemas.py`. Se introdujo validación estricta postgis (`ST_IsValid`, `ST_Intersects`). Los campos `ancho_izquierdo_m` y `ancho_derecho_m` son opcionales según lo aprobado administrativamente, requiriendo en su lugar un `Polygon` o `MultiPolygon` consolidado, y rechazando `FeatureCollection` para prevenir carga excesiva.
3. **Servicios y Rutas Backend:** Se agregó `importar_franja` que archiva la versión anterior e inicia la nueva en una única transacción con trazabilidad de baja lógica. `afectaciones_service.py` intercepta ahora `ST_Intersects` con la franja activa.
4. **Frontend:** Se implementó `FranjaDerechoViaPanel.jsx` accesible desde el visor del tramo en `Mapa.jsx`, permitiendo a los geógrafos cargar archivos `.geojson` con validación previa de consolidación (evitando colecciones dispersas) y enviarlos junto con los atributos de fuente y vigencia.

Modelo mínimo implementado:

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

### Cierre Financiero (Pago Suficiente): Terminado

Se implementó y validó la propuesta de **Cierre Financiero estricto**.

1. **Migración 011 aplicada:** Introduce preflight para proteger históricos,
   añade la validación `2B_PAGO_INSUFICIENTE` en
   `fn_2b_validar_fifonafe`, añade el trigger
   `trg_2b_validar_suficiencia_pago` y recalcula
   `vw_afectacion_ciclo_estado`. Su corrección transaccional, restauración
   aislada, aplicación activa y rechazo de repetición fueron validados el 10
   de agosto de 2026.
2. **Backend:** Se intercepta el completado de indemnización en `flujo.py` verificando el límite mediante la base de datos (con protección 409). Las pruebas de integración en `test_subcorte_2b.py` cubren los casos negativos.
3. **Frontend:** `FlujoLiberacionPanel.jsx` bloquea la transición a completo cuando `saldo_disponible > 0`. `PagosPanel.jsx` muestra una advertencia de falta de fondos cuando aplica.
4. Las pruebas automatizadas fallan si falta `TEST_ADMIN_EMAIL` en `.env`.

### Siguiente incremento aprobado — Administración territorial y de accesos

**Estado:** implementación completa y validada; UAT local activa en 015 y
aceptación funcional manual por los cuatro roles pendiente.

#### Motivo

Antes de este incremento el backend exponía contratos para proyectos, tramos,
`tramo_nucleo`, usuarios y asignaciones `usuario_tramo`, pero el frontend sólo
ofrecía dashboard, mapa y expedientes. Las nuevas vistas administrativas cierran
esa brecha para la operación normal; el fixture queda reservado para preparar
un ambiente UAT aislado.

El incremento debe cubrir la Fase 1 descrita en el proceso funcional, antes de
la operación cotidiana de los expedientes:

```text
Proyecto
└── Tramo
    ├── Franja de derecho de vía versionada
    └── Tramo_Núcleo                 expediente maestro territorial
        └── Afectación               subexpediente confirmado posterior
```

Crear un proyecto no crea por sí mismo un expediente. El expediente maestro
nace únicamente cuando se registra de manera explícita un `tramo_nucleo`. La
importación o selección de un núcleo no debe crear, inferir ni duplicar esa
relación automáticamente.

#### Pantallas y recorridos requeridos

1. **Administración → Proyectos**
   - Listar, buscar y consultar proyectos activos.
   - Crear y editar un proyecto.
   - Darlo de baja lógicamente, con motivo y respetando dependencias activas.
   - Abrir el detalle del proyecto para administrar sus tramos.
2. **Proyecto → Tramos**
   - Listar y filtrar los tramos del proyecto.
   - Crear y editar un tramo con sus datos y geometría.
   - Darlo de baja lógicamente con motivo.
   - Abrir la administración territorial del tramo.
3. **Tramo → Derecho de vía y núcleos**
   - Consultar y versionar la franja de derecho de vía mediante el mecanismo ya
     implementado, sin duplicar su lógica.
   - Seleccionar un núcleo existente o importarlo con las reglas vigentes del
     Corte 5.
   - Revisar geometría, intersección y contexto territorial antes de asociarlo.
   - Crear explícitamente `tramo_nucleo`, con consecutivo, longitud, geometría,
     observaciones y condiciones especiales aplicables.
   - Después de guardar la relación, ofrecer acceso al expediente maestro en
     `/expedientes/:id_tramo_nucleo`.
4. **Administración → Usuarios**
   - Listar, crear y editar usuarios sin exponer credenciales ni hashes.
   - Asignar rol, activar o dar de baja lógicamente.
   - Utilizar los mecanismos existentes de desbloqueo y revocación de sesiones.
5. **Usuario → Tramos asignados** o **Tramo → Equipo**
   - Consultar asignaciones activas.
   - Asignar uno o varios tramos mediante `usuario_tramo`.
   - Retirar o reactivar una asignación con el motivo obligatorio y la auditoría
     existente.

Las vistas quedaron integradas en el layout y React Router existentes como
`/administracion/territorio` y `/administracion/usuarios`, sin duplicar una
misma operación en interfaces separadas.

#### Reglas obligatorias del incremento

- Reutilizar la jerarquía aprobada `Proyecto → Tramo → Tramo_Núcleo`; no crear
  una entidad paralela ni reintroducir `Frente`.
- No crear una afectación durante la configuración territorial. La afectación
  se registra después, cuando derecho, superficie, geometría y sujetos están
  confirmados.
- No inferir `tramo_nucleo` por intersección, nombre, cercanía o importación.
- Mantener autorización por rol y pertenencia territorial también en backend;
  ocultar controles en React no sustituye la autorización.
- Mantener bajas lógicas con motivo; no ejecutar `DELETE` físico.
- Configurar el contexto de auditoría antes de cada escritura y conservar la
  trazabilidad de reactivaciones, bajas y asignaciones.
- Validar geometrías y pertenencia en PostgreSQL y backend, no sólo en el mapa o
  en Pydantic.
- No exponer secretos, hashes, excepciones internas ni datos de otros
  territorios.
- Mostrar estados de carga, vacío, error, acceso denegado, éxito y conflicto;
  un error del API no debe presentarse como una lista vacía válida.
- Conservar operaciones compuestas dentro de una sola transacción cuando una
  acción de usuario escriba varias entidades; contemplar repetición y
  concurrencia.

#### Autorización aprobada e implementada

La decisión funcional DF-01 aprobó que sólo `admin` administre proyectos,
tramos, relaciones `tramo_nucleo`, usuarios y asignaciones. El `geografo`
conserva edición de geometrías, franjas e importaciones en cualquiera de sus
tramos asignados; no queda atado a un único tramo. `operador` y `visualizador`
mantienen el acceso operativo o de lectura que corresponda únicamente sobre su
territorio asignado. La API aplica esta matriz aunque el cliente invoque una
ruta directamente.

#### Implementación validada

- `/administracion/territorio` permite buscar, listar activos o inactivos,
  crear, editar, dar de baja y reactivar proyectos, tramos, núcleos y
  `tramo_nucleo`; la asociación es siempre explícita y ofrece navegación al
  expediente maestro.
- `/administracion/usuarios` permite buscar, crear, editar, desbloquear,
  revocar sesiones, dar de baja y reactivar usuarios. Las asignaciones por
  tramo se reemplazan atómicamente desde la administración territorial.
- El router y servicio administrativos aíslan las operaciones de composición,
  validan padres y usuarios activos y configuran auditoría. Las bajas siguen
  siendo lógicas y requieren motivo.
- La migración 015 protege en PostgreSQL la integridad crítica y el último
  administrador. La autenticación compara correos normalizados sin distinguir
  mayúsculas y minúsculas.
- `backend/scripts/seed_uat.py` prepara idempotentemente cuatro roles, un
  proyecto, dos tramos con un escenario permitido y otro denegado, franjas,
  núcleos, `tramo_nucleo` y parcela; sólo admite bases marcadas como test/UAT y
  exige contraseñas suministradas por variables de entorno.
- Docker Compose persiste `/app/uploads` en un volumen nombrado y el override
  de desarrollo conserva el montaje local existente.

#### Preparación UAT complementaria

El fixture no sustituye las pantallas anteriores. Debe servir para crear de
forma reproducible un ambiente UAT aislado con un proyecto, al menos dos tramos,
franjas activas, municipios, núcleos, relaciones `tramo_nucleo`, una parcela y
usuarios de cada rol con territorios permitidos y denegados. La base UAT no debe
ser utilizada por la suite automatizada ni compartir datos con desarrollo.

Antes de validar el flujo documental con usuarios, `/app/uploads` debe contar
con almacenamiento persistente fuera de la capa escribible del contenedor. La
aceptación debe incluir escenarios de administrador, operador, geógrafo y
visualizador; acceso permitido y denegado; alta territorial completa; rutas
colectiva e individual; documentos; errores; reintentos y concurrencia.

El aprovisionamiento técnico ya está completo en `software_pa_uat`: fixture
ejecutado dos veces para comprobar idempotencia, 015 aplicada, almacenamiento
persistente configurado y los cuatro inicios de sesión validados. Falta la
aceptación manual del proceso; el fixture no constituye por sí mismo esa
aceptación.

#### Orden incremental

1. ~~Confirmar la matriz de autorización y evaluar los contratos existentes.~~
2. ~~Agregar pruebas de reglas y autorización a los endpoints base.~~
3. ~~Implementar navegación administrativa y proyectos.~~
4. ~~Implementar tramos y reutilizar la administración de franjas.~~
5. ~~Implementar selección/importación de núcleos y alta explícita de
   `tramo_nucleo`.~~
6. ~~Implementar usuarios y asignaciones territoriales.~~
7. ~~Crear el fixture UAT aislado y el almacenamiento documental persistente.~~
8. Se aprobaron regresión backend, PostgreSQL aislado, rutas, lint, build y E2E
   administrativo en escritorio y móvil. Falta ejecutar en UAT el recorrido
   funcional completo con admin, operador, geógrafo y visualizador.

#### Criterios mínimos de aceptación

- Un usuario autorizado puede preparar desde el frontend la jerarquía completa
  hasta obtener un expediente maestro navegable, sin usar SQL ni llamadas
  manuales a la API.
- La creación de `tramo_nucleo` exige una confirmación explícita y nunca ocurre
  como efecto lateral de importar un núcleo.
- Cada rol ve y ejecuta únicamente las acciones aprobadas y los datos de sus
  territorios; los intentos directos contra la API también son rechazados.
- Bajas, reactivaciones y asignaciones quedan auditadas y no eliminan físicamente
  registros operativos.
- Los errores de validación, autorización, concurrencia y red se distinguen de
  estados vacíos legítimos.
- El fixture permite repetir el escenario UAT en una base aislada y los archivos
  cargados sobreviven a la recreación del contenedor backend.
- Las pruebas de regresión, frontend y E2E pasan sin desactivar restricciones ni
  reutilizar la base UAT como base automatizada.

Los criterios técnicos y del recorrido administrativo automatizado están
cumplidos. La aceptación integral del proceso por los cuatro roles permanece
pendiente en `software_pa_uat`; no debe declararse aceptación operativa antes
de completar y registrar ese recorrido manual.

## 9. Trabajo técnico transversal pendiente

- Conservar y probar periódicamente la restauración del respaldo previo a 006
  ubicado en `backups/software-pa-db_trenes_pre_006_20260803.dump`.
- Conservar el respaldo previo a 007 de este entorno local:
  `backups/pre_migracion_007_20260804.dump`.
- Conservar el respaldo restaurable previo a 011 y a la recuperación F-01A:
  `backups/pre_011_auth_recovery_restorable_20260810.dump`.
- Conservar el respaldo previo a 012:
  `backups/pre_012_corte5_regularizacion_20260811.dump`.
- Conservar el respaldo previo a 013:
  `backups/pre_013_corte5_auditoria_20260811.dump`.
- Conservar el respaldo previo a 014:
  `backups/pre_014_corte5_nucleos_20260811.dump`.
- Conservar el respaldo previo a 015:
  `backups/db_trenes_pre_015_20260812.dump`.
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

La siguiente tarea no es reimplementar la administración, crear otra entidad
Proyecto, cambiar la jerarquía territorial, repetir Adaptaciones 2.0, rediseñar
2A ni reimplementar 2B. Debe ejecutar y registrar la aceptación funcional del
incremento ya implementado sobre la UAT activa en 015.

Próximo paso operativo:

1. Modelar desde el frontend el flujo real con admin, operador, geógrafo y
   visualizador, incluyendo territorio permitido/denegado, rutas colectiva e
   individual, documentos, reintentos y concurrencia.
2. Registrar defectos técnicos reproducibles sin alterar los datos para ocultar
   fallos. El escenario se repone idempotentemente con `python -m scripts.seed_uat`.
3. No tratar la falta del ambiente HTTPS de aceptación como bloqueo general del
   desarrollo local; registrarla únicamente como gate pendiente para cierre de
   Corte 4 o liberación operativa.
4. Antes de declarar Corte 4 terminado, validar detrás del TLS real del ambiente
   de aceptación: cookie
   `Secure`, origen HTTPS exacto y, si se requiere IP cliente, proxies
   confiables configurados por IP exacta. El ambiente puede ser interno de
   oficina/VPN; no requiere exposición pública a Internet, pero sí nombre
   estable, certificado confiable para Chromium/Firefox y ausencia de
   advertencias TLS.
   *(Nota: La contracción de código de bearer/JWT a nivel local fue completada y
   validada estructuralmente el 6 de agosto de 2026. `python-jose`, tests legacy
   y dependencias obsoletas fueron eliminados).*
5. Ejecutar aceptación E2E de login, quinto fallo, desbloqueo, expiración,
   logout y RBAC/territorio en navegadores soportados, utilizando el TLS real
   del ambiente de aceptación.
6. Replicar 008 y luego 009 en otros ambientes sólo después de respaldo,
   verificación individual de 004/005/006/007 y preflight de bitácora sensible.
7. Revisar y confirmar el diff antes de commit/push.
El derecho de vía versionado está aprobado y terminado como componente del Corte
5, al igual que el Dashboard Analítico y el Uploader Masivo GeoJSON. La
regularización correctiva de estos componentes quedó implementada y validada
el 11 de agosto de 2026 mediante las migraciones 012, 013 y 014 y la regresión
de 125 pruebas tanto en restauración aislada como sobre la base activa.
