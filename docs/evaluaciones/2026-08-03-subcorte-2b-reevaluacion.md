# Reevaluación técnica e implementación — Subcorte 2B

**Fecha:** 2026-08-03  
**Propuesta evaluada:** `docs/propuestas/2026-08-03-subcorte-2b-propuesta.md`  
**Evaluación anterior:** `docs/evaluaciones/2026-08-03-subcorte-2b-evaluacion.md`  
**Rama observada:** `feature/backend-logica`

## 1. Trabajo vigente identificado

`ESTADO_PROYECTO.md` identifica como siguiente trabajo el **Subcorte 2B del
Corte principal 2: secuencia, salidas terminales y estado de liberación por
afectación**. El alcance comprende enlazar las etapas existentes, detener la
ruta ordinaria en las dos salidas terminales, separar estados operativo,
registral, financiero y de liberación, y agregar correctamente los resultados.

No comprende la navegación/aislamiento documental de 2C, avalúos, propiedad
privada, catastro, Registro Público, seguimiento de expropiaciones o
comunidades indígenas, ni el derecho de vía versionado del Corte 5.

## 2. Resumen de la propuesta evaluada

La propuesta corregida introduce una migración expansiva 006, una identidad
estable `afectacion_ciclo`, vínculos inequívocos entre etapas, estados
derivados, terminalidad, control financiero por ciclo, autorización
territorial, operaciones API de transición, UI mínima y pruebas multinivel.

Incorpora las decisiones aprobadas por el usuario:

- individual: el ciclo concluye con la indemnización activa en `completo`;
- colectivo: exige además la asamblea de `retiro_fondos` en `completo` del
  mismo ciclo;
- el modificatorio sustituye definitivamente los montos del convenio base,
  nunca los suma;
- colectivo usa como límite el nuevo `monto_100 + monto_bdt` e individual el
  nuevo `monto_100`, con `monto_90` incluido en `monto_100`.

## 3. Hallazgos de auditoría

### 3.1 Hallazgos resueltos por decisiones funcionales

Los bloqueos D-01 y D-04 de la evaluación anterior quedaron resueltos. Ya es
posible construir una regla inequívoca de conclusión, vigencia, saldo y
liberación sin usar como sustituto el monto pagado o `tipo_pago='total'`.

### 3.2 Ajustes técnicos incorporados durante esta reevaluación

1. La propuesta no explicitaba cómo abrir un ciclo posterior antes de sus
   actividades. Se añadieron `GET/POST /api/afectaciones/{id}/ciclos`; el
   ciclo original nace atómicamente con la afectación y no se crea desde un
   convenio de forma implícita.
2. Se precisó la activación del modificatorio: siempre exige firma; el
   colectivo exige también su inscripción RAN aplicable, mientras que el
   individual no inventa una inscripción propia porque la fuente canónica la
   exceptúa expresamente.
3. La migración debe mantener nulas las nuevas referencias históricas
   ambiguas. Sólo puede crear la raíz estructural original por afectación; no
   puede atribuir actividades, asambleas, convenios o trámites históricos por
   cercanía temporal.
4. Los endpoints heredados constituyen rutas de bypass. Deben delegar en el
   servicio 2B o quedar protegidos por las mismas precondiciones, roles y
   territorio; PostgreSQL conserva la defensa ante escrituras externas.

### 3.3 Evidencia del repositorio y de la base activa

- `docs/Descripción proceso.md` conserva sensibilización/caminamiento
  originales en `tramo_nucleo`, exige RAN antes de FIFONAFE y exceptúa al
  modificatorio individual de una nueva inscripción.
- Requirements 7, 8, 9, 11, 19, 20, 21, 23 y 37 sustentan asamblea colectiva,
  variantes, no conflictos, liberación posterior al pago, terminalidad,
  ciclos completos y límite pagable.
- Las migraciones 004/005 protegen dinero exacto, auditoría, linaje básico y
  separación colectiva/individual, pero no modelan ciclos ni liberación.
- La base activa tiene 004 y 005, seis afectaciones activas, dos convenios,
  cero trámites FIFONAFE y cero pagos. No contiene columnas/vistas 2B.
- `main.py` concentra CRUD que permite saltos, expone mensajes derivados de
  `exc.orig`, admite al geógrafo en escrituras de negocio y no aplica
  `usuario_tramo` por recurso.
- El frontend no captura el circuito completo y todavía calcula elegibilidad
  financiera localmente; las fixtures históricas crean afectaciones sin los
  antecedentes exigidos.

## 4. Matriz de evaluación

| Área | Resultado | Evidencia | Ajuste requerido |
|---|---|---|---|
| Alcance | Aprobada | `ESTADO_PROYECTO.md`, Subcorte 2B. | Mantener 2C/Corte 5 fuera. |
| Secuencia ordinaria | Aprobada | Flujograma resumido, descripción canónica y Requirement 37. | Proteger API y PostgreSQL. |
| Pago concluido | Aprobada | Decisión D-01 aprobada. | Derivar por ruta, no por suma ni `tipo_pago`. |
| Modificatorio | Aprobada con ajustes | Decisión D-04 y excepción registral individual documentada. | Vigencia explícita, bloqueo por ciclo y activación diferenciada. |
| Ciclos | Aprobada con ajustes | Requirements 20/21 y repetibilidad. | Apertura explícita; original atómico. |
| Datos históricos | Aprobada con ajustes | Seis afectaciones sin antecedentes realizados. | Sin asociaciones inferidas; anomalía visible. |
| Integridad DB | Aprobada con ajustes | 004/005 ya usan constraints/triggers y `NUMERIC`. | Ampliar con FK compuestas, transición y concurrencia. |
| ORM/contratos | Aprobada con ajustes | Modelos reflejan 005; contratos CRUD permiten saltos. | Añadir estructuras 2B y DTO de transición. |
| Servicios/atomicidad | Aprobada con ajustes | Existe `SET LOCAL` de auditoría, pero lógica dispersa. | Servicio central, una transacción por operación. |
| Endpoints | Aprobada con ajustes | Rutas heredadas en `main.py`. | Evitar bypass y duplicados. |
| Rol/territorio | Aprobada con ajustes | `usuario_tramo` existe y no se usa por recurso. | Admin global; demás usuarios sólo tramos activos; geógrafo sin escritura de negocio. |
| Auditoría/errores | Aprobada con ajustes | Triggers y contexto existen; handlers filtran `exc.orig`. | Contexto obligatorio y mensajes de dominio seguros. |
| Frontend | Aprobada con ajustes | Faltan actividades, ciclo, FIFONAFE y estado autoritativo. | UI mínima 2B sin absorber 2C. |
| Pruebas | Aprobada con ajustes | Estrategia suficiente; fixtures actuales saltan secuencia. | Fábricas válidas, negativos DB/API, seguridad, concurrencia y base aislada. |

## 5. Resultado de los gates

| Gate | Resultado | Evidencia |
|---|---|---|
| Funcional | **Superado** | D-01/D-04 están implementadas y las rutas individual, colectiva, terminal y modificatoria pasan en integración. |
| Datos | **Superado** | 006 instaló FK, ciclo estable, vigencia única, vistas y bloqueo de raíz; no quedaron ciclos huérfanos ni raíces faltantes. |
| Seguridad | **Superado** | La suite verifica denegación sin asignación, acceso posterior a `usuario_tramo`, filtros de listas y roles de escritura. |
| Arquitectura | **Superado** | `tramo_nucleo` conserva antecedentes, `afectacion_ciclo` aísla ramas y el dominio 2B reside en servicio/router propios sin invadir 2C. |
| Migración | **Superado** | 006 terminó en `COMMIT` sobre copia lógica, conserva la base activa en 005 y rechaza reaplicación antes de alterar. |
| Pruebas | **Superado** | 104 pruebas, consultas de integridad/vistas, OpenAPI, lint y build aprobados. |

## 6. Propuesta corregida

Se aprueba la propuesta únicamente con los ajustes de apertura explícita de
ciclos, activación registral diferenciada del modificatorio, compatibilidad
histórica sin inferencias y cobertura de todos los endpoints alternativos.
Estos ajustes ya están incorporados en la propuesta evaluada.

## 7. Decisión de viabilidad

La propuesta corregida supera los gates de diseño. No queda una decisión
funcional indispensable pendiente, por lo que **es viable iniciar una
implementación incremental**. El estado sólo podrá cambiar a implementación
completa y validada tras aplicar 006 en una base aislada y ejecutar las
pruebas documentadas.

## 8. Plan final de implementación

1. Escribir casos de reglas y adaptar fábricas de flujo válido.
2. Crear la migración 006 expansiva con preflight, vínculos, funciones,
   triggers, índices y vistas derivadas.
3. Alinear ORM y contratos con dinero `Decimal`.
4. Implementar acceso territorial y servicio transaccional de flujo.
5. Proteger rutas heredadas y añadir operaciones específicas 2B.
6. Implementar la UI mínima de expediente/afectación y eliminar decisiones
   financieras autoritativas del navegador.
7. Aplicar 006 únicamente a una base aislada, ejecutar pruebas DB/API,
   regresión, build/lint e integración.
8. Actualizar las secciones 6, 7 y 8 de `ESTADO_PROYECTO.md` sólo con hechos
   verificados.

## 9. Cambios realizados

| Archivo | Cambio | Justificación |
|---|---|---|
| `backend/db/migrations/006_subcorte_2b_secuencia_estados.sql` | Migración expansiva con `afectacion_ciclo`, terminalidad, vínculos nulos compatibles, vigencia financiera, FK/índices/triggers, bloqueo por ciclo y cuatro vistas derivadas. | Representar la secuencia y protegerla también ante SQL directo, sin inferir asociaciones históricas. |
| `backend/app/models.py` | Mapeo de ciclo, terminalidad, linaje FIFONAFE y vigencia de convenios. | Mantener ORM alineado con 006. |
| `backend/app/schemas.py` | DTO de ciclos, estados y transiciones; contratos de linaje y campos FIFONAFE. | Separar captura de hechos de estados derivados y conservar dinero como `Decimal`. |
| `backend/app/services/access.py` | Verificación y filtrado por `usuario_tramo` para tramos, expedientes, núcleos y afectaciones. | Evitar IDOR y exposición entre territorios. |
| `backend/app/services/flujo.py` | Operaciones atómicas de ciclo, terminalidad, indemnización, retiro, activación de modificatorio y consulta de estado. | Centralizar intención de dominio y bloqueo concurrente. |
| `backend/app/routers/flujo.py` | Endpoints específicos de transición y estado 2B. | Evitar usar actualizaciones CRUD genéricas como comandos de negocio. |
| `backend/app/main.py` | Integración del router; protección de rutas heredadas, roles/territorio, linaje compatible y errores genéricos seguros. | Cerrar bypass y conservar contratos existentes cuando la relación es inequívoca. |
| `backend/app/routers/pagos.py` | Filtro y autorización territorial de pagos. | Proteger el circuito financiero por recurso. |
| `backend/tests/conftest.py`, `test_crud_ciclo_vida.py`, `test_fase2_adaptaciones.py` | Datos semilla y regresiones adaptados a una secuencia válida. | Evitar que la suite valide saltos que 2B debe prohibir. |
| `backend/tests/test_subcorte_2b.py` | Ocho pruebas de reglas, concurrencia, cierre, terminalidad, modificatorios y territorio. | Cubrir decisiones D-01/D-04 y gates críticos. |
| `backend/tests/test_zzz_limpieza.py` | Limpieza por reintentos de dependencias temporalmente bloqueadas. | Respetar los triggers financieros sin dejar residuos ni desactivarlos. |
| `frontend/src/components/fase2/FlujoLiberacionPanel.jsx` | UI mínima para actividades, ciclos, terminalidad, FIFONAFE, indemnización y retiro. | Permitir ejecutar la secuencia sin invadir el aislamiento documental de 2C. |
| `frontend/src/components/fase2/PagosPanel.jsx` | Saldo y límite obtenidos del estado autoritativo del backend. | Eliminar la decisión financiera local y el riesgo de suma incorrecta. |
| `frontend/src/pages/ExpedienteDetail.jsx`, `FormAsamblea.jsx`, `FormConvenio.jsx` | Integración del flujo y captura explícita de afectación/ciclo/padre; modificatorio activable. | Mantener linaje consistente entre interfaz, API y base. |
| `docs/propuestas/2026-08-03-subcorte-2b-propuesta.md` | Se incorporó la superficie base inmutable por ciclo. | Evitar duplicar superficie al sustituir versiones financieras. |
| `ESTADO_PROYECTO.md` | Estado, reglas, migración, evidencias y siguiente trabajo actualizados. | Reflejar sólo implementación y validaciones realmente ejecutadas. |

## 10. Migraciones y compatibilidad

- La 006 exige 005, toma un bloqueo asesor, usa una transacción única y
  registra su versión sólo al final.
- Se aplicó con `ON_ERROR_STOP=1` sobre `db_trenes_2b_test_final5`, copia
  lógica de `db_trenes`; terminó en `COMMIT`.
- Creó una raíz `cop_original` por cada afectación, incluida la superficie
  confirmada, sin asociar actividades, asambleas, convenios o trámites.
- Los nuevos vínculos históricos permanecen `NULL` cuando no son
  inequívocos. Los endpoints sólo aplican compatibilidad automática en el
  ciclo original único o cuando el convenio proporciona el linaje.
- La base activa no fue modificada: conserva versiones 004/005 y no contiene
  `afectacion_ciclo`.
- Las bases temporales `db_trenes_2b_test*` se eliminaron al terminar; una
  consulta a `pg_database` confirmó que `db_trenes` permaneció disponible.
- No se ejecutó una migración inversa destructiva ni una corrección silenciosa
  de datos.

## 11. Pruebas y validaciones

| Validación | Comando | Resultado | Estado |
|---|---|---|---|
| Aplicación 006 aislada | `docker compose exec -T db psql -v ON_ERROR_STOP=1 -U alfredo -d db_trenes_2b_test_final5 < backend/db/migrations/006_subcorte_2b_secuencia_estados.sql` | Transacción completada y versión 006 registrada. | Aprobada |
| Regresión e integración | `docker compose run --rm --no-deps -e DB_NAME=db_trenes_2b_test_final5 backend pytest -q --tb=short` | `104 passed`, una advertencia de deprecación de Starlette. | Aprobada |
| Integridad posterior | Consultas de raíces, huérfanos y vistas en la copia | 0 afectaciones sin ciclo original, 0 ciclos huérfanos; vistas consultables. | Aprobada |
| Terminalidad en PostgreSQL | Transacción que marca salida heredada e intenta insertar otro ciclo | Rechazo `2B_FLUJO_TERMINAL`; bandera e inserción revertidas. | Aprobada |
| Guardia de reaplicación | Segunda ejecución de 006 con `ON_ERROR_STOP=1` | Rechazo previo: `La migración 006 ya fue aplicada`. | Aprobada |
| Base activa inalterada | Consulta a `db_trenes.schema_migrations` y `to_regclass` | Sólo 004/005; `afectacion_ciclo` no existe. | Aprobada |
| Lint frontend | `npm run lint` | 0 errores y 0 advertencias. | Aprobada |
| Build frontend | `npm run build -- --outDir /tmp/software-pa-frontend-dist-final --emptyOutDir` | Producción exitosa; chunk mayor 289.34 kB. | Aprobada |
| Higiene del diff | `git diff --check` | Sin errores de espacios o marcadores. | Aprobada |
| Rutas API | Inspección de OpenAPI por método/path | Sin duplicados. | Aprobada |

Durante la validación se detectaron y corrigieron dos defectos: un campo de
superficie colocado inicialmente en el DTO equivocado y una limpieza que
intentaba retirar modificatorios antes que sus pagos. La corrida registrada
arriba parte de otra copia limpia y contiene ambas correcciones.

## 12. Riesgos restantes

- El despliegue real sigue pendiente: aplicar 006 en cada ambiente requiere
  respaldo, suspensión de escrituras, preflight y verificación posterior.
- Las asociaciones históricas ambiguas permanecen nulas y requieren
  conciliación documental manual; esto es compatibilidad deliberada, no una
  liberación automática.
- Falta aceptación funcional con usuarios y datos representativos para los
  recorridos colectivo, individual, terminal, modificatorio y mixto.
- Clientes antiguos que intenten saltar la secuencia recibirán `409` hasta
  capturar sus antecedentes aplicables.
- Persiste una advertencia de deprecación en la integración
  Starlette/httpx; no afecta el resultado funcional actual.
- El directorio `frontend/dist` conserva permisos preexistentes que impiden
  sobrescribirlo localmente; el build validado se generó en `/tmp`.

## 13. Actualización realizada en `ESTADO_PROYECTO.md`

Se actualizaron fecha y continuidad, archivos/rutas, reglas de cierre y
modificatorios, historial de la 006, trabajo realizado, estado real de la base
activa, situación del Subcorte 2B, pendientes y la instrucción para continuar.
Se dejó explícito que `db_trenes` permanece en 005 y que 2C sólo debe comenzar
después del despliegue controlado de 006.

## 14. Estado final

**Implementación completa y validada.**

La evidencia es la aplicación transaccional de 006 sobre una copia lógica
representativa, 104 pruebas aprobadas, consultas de integridad/vistas, lint y
build exitosos. “Validada” describe el artefacto de la rama en el ambiente
aislado; no significa que la migración esté aplicada en la base activa ni que
se haya completado la aceptación de usuario o el despliegue.

## 15. Adenda de despliegue en base activa

Después de cerrar esta evaluación, el usuario autorizó expresamente aplicar
006 sobre `db_trenes`. Las afirmaciones anteriores sobre una base activa en
005 describen el momento de la evaluación y quedan actualizadas por esta
adenda.

El despliegue del 3 de agosto de 2026 se realizó así:

1. Preflight sobre 004/005: seis afectaciones activas, dos convenios activos,
   cero trámites/pagos activos y cero terminales padre contradictorias.
2. Backend y scheduler detenidos durante la ventana de escritura.
3. Respaldo custom de PostgreSQL validado con `pg_restore`, 418,744 bytes y
   SHA-256 `85a9cece607d83330c6132870e61a55e89e311798e40ca3b95cbb4c7b5fc7757`,
   conservado en `backups/software-pa-db_trenes_pre_006_20260803.dump`. Una
   restauración completa temporal recuperó 004/005 y los conteos previos; la
   base de comprobación se eliminó después.
4. Aplicación con `psql -v ON_ERROR_STOP=1`; resultado `BEGIN` a `COMMIT` y
   registro único de versión 006.
5. Postflight: 20 ciclos originales, seis activos, cero afectaciones sin raíz,
   cero ciclos huérfanos y cero vigencias financieras duplicadas. Las seis
   afectaciones permanecieron pendientes; no se infirió ninguna liberación.
6. Backend y scheduler reanudados. Raíz y OpenAPI respondieron 200, las rutas
   2B quedaron publicadas y el endpoint protegido respondió 401 sin token.

La aceptación funcional con usuarios, el commit y el push siguen pendientes.
La base activa sí contiene ahora 004, 005 y 006.
