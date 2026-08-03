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

**Última actualización:** 31 de julio de 2026

**Rama de trabajo:** `feature/backend-logica`

**Próximo trabajo funcional:** Subcorte 2B del Corte principal 2: secuencia,
salidas terminales y estado de liberación por afectación, sobre la base ya
reforzada por el Subcorte 2A.

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
2. El flujograma externo `flujograma propiedad social.pdf`, como fuente
   funcional, y su resumen `docs/Descripción proceso.md`.
3. `docs/Flujo liberacion derechos.md`.
4. `docs/Estructura Datos.md`.
5. `docs/Diccionario_Datos_SSALFER.md`.
6. `docs/requirements.md`.
7. Las migraciones `001`, `002`, `003`, `004` y `005` en orden, como fuente
   del esquema ejecutable.
8. `docs/Diseno_Subcorte_2A.md`, como registro de la separación ya
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

### Próxima migración

El siguiente trabajo de base de datos corresponde al Subcorte 2B, si su diseño
confirma que hacen falta nuevas restricciones, estados, vistas o tipos
documentales para representar secuencia, salidas terminales y liberación.

No eliminar columnas heredadas hasta desplegar y validar el Corte principal 2.
La contracción de columnas heredadas de Adaptaciones 2.0 queda reservada para
una migración posterior.

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

En la revisión del 30 de julio no existía un archivo `.env`, por lo que no se
volvió a consultar la base activa. Antes de diseñar o ejecutar la próxima
migración se debe configurar el entorno local y verificar directamente
tablas, restricciones, triggers, vistas y versiones aplicadas; no se debe
inferir ese estado únicamente de esta nota histórica.

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
- La vista vigente `vw_tramo_nucleo_estado` clasifica expropiación como
  `problema` y considera `liberado` cuando las afectaciones tienen convenio
  inscrito en el RAN. Esa lógica es heredada y debe sustituirse: las salidas
  terminales requieren estado propio y la liberación ordinaria ocurre después
  del pago.
- Las banderas actuales viven en `nucleo_agrario` y `tramo_nucleo`; no existe
  todavía una salida terminal específica por `afectacion`.
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
7. Hacer cumplir la secuencia obligatoria con las entidades existentes y
   calcular avance legal, geoespacial y financiero por afectación.
8. Migrar o vincular datos existentes sin inferir relaciones ambiguas.
9. Añadir pruebas de aislamiento: datos de una afectación no deben aparecer
   en otra del mismo `tramo_nucleo`.
10. Corregir el panel documental para usar
    `entidad_relacionada_tipo = 'afectacion'` e
    `entidad_relacionada_id = id_afectacion`.
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

#### Subcorte 2B propuesto — Secuencia, excepciones y estado

Después de reforzar colectiva/individual:

1. Enlazar las etapas existentes para impedir saltos inválidos.
2. Incorporar salidas terminales por afectación y su agregación en
   `tramo_nucleo`.
3. Separar progreso registral, financiero, terminal y liberación.
4. Derivar `liberado` después del pago aplicable.
5. Probar rutas colectiva, individual, terminal y expediente mixto.

#### Subcorte 2C propuesto — Navegación y aislamiento documental

1. Mantener el expediente maestro de `tramo_nucleo`.
2. Abrir cada afectación en su propio subexpediente.
3. Mostrar antecedentes compartidos sin duplicarlos.
4. Aislar actuaciones, pagos y documentos propios de cada afectación.
5. Corregir el tipo de relación inválido usado por el panel documental.

### Corte 3 — Seguridad inmediata: parcial

Ya realizado:

- Handler global sin fuga de `str(exc)`.
- Registro interno de excepciones.
- Escape de valores en popups de `Mapa.jsx` para mitigar XSS.
- `docker-compose.yml` consume variables obligatorias del entorno.
- Existe `.env.example` sin secretos reales y `.env` está ignorado por Git.

Pendiente:

- Rotar credenciales y `SECRET_KEY` que ya estuvieron en commits.
- Crear el `.env` local de cada entorno y documentar configuración y
  recuperación.

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

La siguiente tarea no es crear Proyecto, repetir Adaptaciones 2.0 ni volver a
diseñar el Subcorte 2A.

Antes de implementar el Subcorte 2B:

1. Leer los documentos indicados en la sección 3.
2. Confirmar que requisitos y diseño respetan el flujograma de propiedad
   social, las salidas terminales y la definición de `liberado`.
3. Configurar el entorno y verificar que la base activa tenga 004 y 005
   aplicadas cuando corresponda.
4. Auditar modelos, FK, endpoints, vistas y pantallas que participan en la
   secuencia convenio → RAN → FIFONAFE → pago → liberado.
5. Presentar una matriz de estados por afectación que separe progreso
   registral, progreso financiero, salidas terminales y liberación.
6. Proponer la migración expansiva, contratos API, rutas de frontend y plan de
   compatibilidad necesarios para 2B.
7. No editar ni ejecutar una nueva migración hasta validar esa propuesta con
   el usuario.

El Subcorte 2A ya quedó implementado y aplicado en la base local validada
mediante la migración 005. El resto del Corte 2 debe continuar con pruebas de
integridad, regresión, autorización y aislamiento entre afectaciones.

El derecho de vía versionado está aprobado como componente futuro del Corte
5. No debe mezclarse en el Subcorte 2B.
