# ESTADO DEL PROYECTO — SOFTWARE-PA

> **Documento de continuidad para personas y agentes de IA.**
> Leer completo antes de proponer o modificar código. No asumir que la
> numeración de las fases operativas, los cortes principales y los subcortes de
> Adaptaciones 2.0 significan lo mismo.

**Última actualización:** 28 de julio de 2026

**Rama de trabajo:** `feature/backend-logica`

**Próximo trabajo funcional:** Corte principal 2, expediente maestro de
Tramo_Núcleo y subexpedientes operativos por afectación.

## 1. Objetivo y dominio

SOFTWARE-PA gestiona la liberación de derecho de vía ferroviario. Integra
información territorial, agraria, jurídica, social, documental, financiera y
geoespacial.

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
backend/tests/                          regresión e integración
frontend/src/pages/ExpedienteDetail.jsx expediente actual por tramo_nucleo
frontend/src/pages/ExpedientesList.jsx  listado actual de tramo_nucleo
frontend/src/components/fase2/          módulos agregados en Adaptaciones 2.0
```

Contratos HTTP relevantes ya existentes:

```text
GET/POST       /api/proyectos
GET/POST       /api/tramos
GET/POST       /api/tramos-nucleos
GET/POST       /api/afectaciones
GET             /api/afectaciones/{id_afectacion}
GET/POST       /api/convenios
GET/POST       /api/asambleas
GET/POST       /api/actividades-campo
GET/POST       /api/fifonafe
GET/POST       /api/personas
POST            /api/parcelas/con-titular
POST            /api/orvs/con-integrantes
GET/POST       /api/minutas
GET/POST       /api/pagos-indemnizacion
POST            /api/documentacion/{id_documento}/archivo
GET             /api/documentacion/{id_documento}/versiones
GET             /api/alertas/no-vistas
GET             /api/alertas/no-vistas/count
```

Los routers se incluyen con prefijo `/api` desde `main.py`. Antes de agregar
una ruta nueva se debe verificar que no exista ya una combinación igual de
método y path en `main.py` o en otro router.

## 3. Documentos que deben leerse

Orden recomendado para recuperar contexto:

1. Este archivo.
2. `docs/Descripción proceso.md`.
3. `docs/Flujo liberacion derechos.md`.
4. `docs/Estructura Datos.md`.
5. `docs/requirements.md`.
6. `docs/design.md`.
7. `docs/Plan de Trabajo Adaptaciones 2.0.md`.
8. `docs/Implementacion Adaptaciones Fase 2.0.md`.
9. Las migraciones `001`, `002`, `003` y `004` en orden.

`docs/Plan de Trabajo Adaptaciones 2.0.md` describe un trabajo adicional que
se ejecutó entre los cortes principales 1 y 2. Sus subcortes A, B y C no son
los cortes principales 2, 3 y 4.

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

Regla financiera:

```text
valor de la tierra       = convenio.monto_100
anticipo de la tierra    = convenio.monto_90, incluido en monto_100
bienes distintos tierra = convenio.monto_bdt
límite pagable           = monto_100 + monto_bdt
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

### Próxima migración

No crear todavía la migración de contracción que antes se había llamado
`005`. El Corte principal 2 puede necesitar una migración expansiva para
distinguir datos compartidos del expediente maestro y datos propios de una
`afectacion`.

Antes de asignar número debe definirse el diseño. La secuencia recomendada es:

```text
005  expansión para expediente maestro y subexpedientes, si la auditoría
     confirma que hacen falta nuevas FK, tipos documentales o estados
006  contracción de columnas heredadas de Adaptaciones 2.0
```

No eliminar columnas heredadas hasta desplegar y validar el Corte principal 2.

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

## 8. Plan principal vigente de cinco cortes

### Corte 1 — Modelo territorial: terminado

Proyecto + Tramo + Tramo_Núcleo sin Frente + `usuario_tramo`.

### Corte 2 — Expediente maestro y subexpedientes por afectación: siguiente

Decisión aprobada:

```text
tramo_nucleo = expediente maestro territorial de liberación
afectacion   = subexpediente operativo confirmado
```

Situación actual:

- `/expedientes` lista `tramo_nucleo`.
- `/expedientes/:id_tramo_nucleo` abre el expediente maestro, pero su pantalla
  mezcla las actuaciones propias de todas sus afectaciones.
- Asambleas, actividades, minutas, pagos y documentos se consultan
  principalmente por `id_tramo_nucleo`.
- `afectacion` ya es obligatoria en convenio y opcional en FIFONAFE, pero aún
  funciona como registro secundario de la pantalla.
- El panel documental usa actualmente el tipo inválido `tramo_nucleo`. El
  Corte 2 debe soportar expresamente documentos compartidos del expediente
  maestro y documentos propios de una afectación.

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
                ├── inventario/valoración de BDT, cuando aplique
                ├── actuaciones y minutas posteriores
                ├── asamblea, solamente cuando corresponda
                ├── convenio
                ├── FIFONAFE y pagos
                ├── documentos
                └── cierre
```

La sensibilización sigue siendo una etapa explícita previa al caminamiento.
El caminamiento delimita superficie y geometría e identifica bienes distintos
a la tierra. No se crea una afectación preliminar; al registrar la afectación
confirmada, las etapas compartidas permanecen en el expediente maestro y
quedan accesibles desde el subexpediente como antecedentes. Actualmente sólo
existe `convenio.monto_bdt`; no hay inventario detallado de cada BDT. Antes de
crearlo se debe confirmar el nivel de detalle requerido por usuarios.

Al diseñar el corte:

1. Auditar qué entidades son propias de una afectación y cuáles son
   compartidas.
2. Mantener ORV en el nivel del núcleo; no duplicarla por afectación.
3. Definir una transición compatible y una migración expansiva si hace falta.
4. Mantener un endpoint agregado del expediente maestro y agregar el detalle
   operativo por `id_afectacion`.
5. Cambiar navegación y estado para abrir afectaciones dentro de su
   `tramo_nucleo`, sin eliminar la vista maestra.
6. Mostrar sólo las etapas aplicables al tipo colectivo o individual.
7. Calcular avance legal, geoespacial y financiero por afectación.
8. Migrar o vincular datos existentes sin inferir relaciones ambiguas.
9. Añadir pruebas de aislamiento: datos de una afectación no deben aparecer
   en otra del mismo `tramo_nucleo`.
10. Corregir el panel documental para usar
    `entidad_relacionada_tipo = 'afectacion'` e
    `entidad_relacionada_id = id_afectacion`.

No comenzar eliminando `tramo_nucleo` ni trasladando ciegamente todas las FK a
`afectacion`.

### Corte 3 — Seguridad inmediata: parcial

Ya realizado:

- Handler global sin fuga de `str(exc)`.
- Registro interno de excepciones.
- Escape de valores en popups de `Mapa.jsx` para mitigar XSS.

Pendiente:

- Quitar secretos literales de `docker-compose.yml`.
- Consumir un `.env` local ignorado por Git.
- Mantener `.env.example` sin secretos reales.
- Rotar credenciales y `SECRET_KEY` que ya estuvieron en commits.
- Documentar configuración y recuperación.

No copiar las credenciales actuales a documentación nueva.

### Corte 4 — Autenticación formal: pendiente

- Sustituir JWT en `localStorage`.
- Definir cookie HttpOnly o estrategia equivalente.
- Sesiones, revocación y logout real.
- Registro de accesos exitosos y fallidos.
- Bloqueo por cinco intentos fallidos.
- Expiración e inactividad.
- Pruebas de autenticación y autorización.

### Corte 5 — Importación y reportes: pendiente

- Endurecer el importador GeoJSON.
- Limitar tamaño y validar `FeatureCollection`.
- Validar tipo de geometría por entidad.
- Reportar errores por feature.
- Evitar `flush()` antes de establecer una geometría obligatoria.
- Alinear importación con Proyecto → Tramo.
- Dashboard y reportes por proyecto.
- Indicadores por afectación y agregados por tramo/proyecto.

## 9. Trabajo técnico transversal pendiente

- Validación funcional y de experiencia con usuarios finales.
- Decidir si una base limpia necesita conservar
  `persona_fuente_legacy`; hoy es trazabilidad de migración, no una segunda
  identidad maestra.
- Conciliar identidades únicamente si aparecen datos reales heredados.
- Retirar columnas legacy de ORV, parcela y documentos después del nuevo
  flujo y de verificaciones de uso.
- Consolidar posteriormente `001_init_schema.sql` para instalaciones nuevas.
- Rotar secretos ya expuestos en historial.

## 10. Instrucción para continuar

La siguiente tarea no es crear Proyecto ni repetir Adaptaciones 2.0.

Antes de implementar el Corte principal 2:

1. Leer los documentos indicados en la sección 3.
2. Auditar modelos, FK, endpoints y pantallas que hoy usan
   `id_tramo_nucleo`.
3. Presentar una matriz entidad por entidad indicando si debe quedar en
   `tramo_nucleo`, vincularse a `afectacion` o ser compartida.
4. Proponer la migración expansiva, contratos API, rutas de frontend y plan de
   compatibilidad.
5. No editar ni ejecutar una migración hasta validar esa propuesta con el
   usuario.

Después de aprobar el diseño se implementará el Corte 2 con pruebas de
integridad, regresión, autorización y aislamiento entre afectaciones.
