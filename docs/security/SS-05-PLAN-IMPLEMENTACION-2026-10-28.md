# SS-05, fase 0: plan de decisión, implementación y pruebas

Fecha: 2026-10-28. Estado: **diseño propuesto, pendiente de aprobación funcional expresa**. No autoriza cambios ni despliegue. Referencia local `dev`, `683ff75613768de28a7127c7e33a6e2ef4fc40ff` más remediaciones previas preservadas.

Leer [comportamiento actual y alternativas](SS-05-ANALISIS-POLITICA-DOCUMENTAL-2026-10-28.md) y [matriz de permisos](SS-05-MATRIZ-DECISION-RBAC-2026-10-28.md). SS-05 sigue Medio/Potencial respecto de la política funcional, sin declaración de filtración demostrada.

## Decisiones para aprobación funcional

| ID | Decisión pendiente / propuesta C | Quién debe decidir y consecuencia |
|---|---|---|
| D01 | Unidad de seguridad: PN y, donde proceda, subexpediente; no heredar por compartir núcleo/parcela. Definir resolución de cada objetivo canónico | Responsable documental y dueño del proceso agrario con AppSec. Proyecto asignado puede ser demasiado amplio para un expediente individual |
| D02 | Conservar lectura de proyectos activos para visualizador/geógrafo o aprobar otra restricción expresamente | Dueño de roles. SS-05 no debe cambiarla por inferencia; admin conserva alcance global sujeto a flujos explícitos |
| D03 | Quién clasifica como compartible, quién consiente por cada participante y quién ejecuta. Propuesta: admin ejecuta con decisión funcional registrada; operador puede solicitar | Responsables de expedientes y administración. No basta que un usuario tenga dos asignaciones; definir delegación, revocación y conflictos, sin inventar otro rol |
| D04 | Selección explícita de versiones pasadas/futuras por ámbito, sin concesión por fecha o por subida. Definir retiro de publicación y acceso histórico autorizado | Responsable documental/archivo. Puede requerir derivado autorizado cuando el archivo mezcla contenido de expedientes |
| D05 | Captura global sobre todos los participantes protegidos o facultad admin explícita; separar anotaciones locales. Nuevo archivo global no implica publicarlo automáticamente | Dueño funcional de captura. Aceptar coordinación adicional o escoger A/B en lugar de C |
| D06 | Desvinculación local, cierre del último vínculo, referencias pendientes y objetivos compartidos | Dueño de expediente. Propuesta: motivo y precondiciones; bloquear cuando afecte a terceros o requiera resolución de evidencia; no borrar FK o histórico |
| D07 | Baja global administrativa; retención y recuperación histórica separadas | Dueño documental con responsables de archivo/jurídico. No asignar plazos legales ni borrar archivos desde esta fase |
| D08 | Participantes suspendidos, proyectos inactivos, retirados y ámbito no resoluble | Responsables de ambos expedientes. Propuesta: no quitarlos silenciosamente de Pguard; revisión admin, congelación/retención formal documentada |
| D09 | Destino de documentos legados compartidos/no clasificables: revisión manual, continuidad temporal aceptada o restricción aprobada al corte | Dueño funcional acepta explícitamente el riesgo/transición. No se presume consentimiento retrospectivo ni se cambia producción en fase0 |
| D10 | Fijar versión/manifiesto como evidencia en requisitos/seguimiento y diferenciarla de “última carga” | Especialistas agrarios/jurídicos y dueño de seguimiento. No recalcular cumplimiento, superficies, montos ni decisiones jurídicas automáticamente |
| D11 | Contrato API/UI contextual, tratamiento de rutas globales, significado de “vigente” y usuarios con varias vistas | Producto/frontend/backend. Probar transición completa; no tolerar bypass por endpoints antiguos |
| D12 | Momento de revocación, operaciones en vuelo, registro de decisiones y control de cambios concurrentes | AppSec/backend/operación. Propuesta: nuevas solicitudes reevaluadas, escrituras revalidadas transaccionalmente; no prometer revocar bytes ya entregados |

La aprobación debe identificar versión de la política, responsables, celdas de la matriz aceptadas, excepciones, criterios QA y plan de transición del legado. No se solicita autorización técnica genérica como sustituto de esa decisión. Se puede elegir A o B: en ese caso reescribir matrices/plan y aceptación antes de programar.

## Cambios técnicos previsibles, no implementados

| Área | Propuesta e impacto |
|---|---|
| Access | Separar `can_read_context`, `can_read_version`, `can_change_global`, `can_add_participant`, `can_unlink_context`, `can_deactivate_global`. Los nombres son conceptuales, no funciones creadas. Resolver el conjunto completo de ámbitos, no el primer proyecto/vínculo autorizado |
| Lecturas por contexto | Contexto validado en servidor, metadatos compartibles más anotación local, versiones aprobadas. No devolver datos de otros participantes en errores, listas, totales, descripciones o capacidades |
| Lecturas globales existentes | No pueden quedar como escape al manifest; exigir contexto verificable o flujo administrativo autorizado con contrato explícito. No seleccionar silenciosamente el primer vínculo para “compatibilidad” |
| Escrituras | Evaluar alcance afectado completo antes del cambio y revalidar frente a vínculos/asignaciones concurrentes. Operador A no modifica el objeto global de B. No cambiar auth/CSRF/roles ni confiar en flag enviado por UI |
| Desvinculación | Nueva operación explícita por vínculo/ámbito, distinta de DELETE D; cierre lógico auditado, no borrado. No habilitar todavía una ruta ni cambiar el significado de DELETE existente |
| Referencias | Mantener FKs globales/historia; referencias no conceden acceso. Validar futura selección de evidencia según lectura y publicación del contexto; no producir una fuga al confirmar que existe una versión fuera de alcance |
| Consolidado | Filtrar procedencias con la misma política, latest **aprobado del contexto**. Puede diferir del máximo global actual; contrato/etiqueta transicional y pruebas frontend necesarias. No interpretar latest como validez jurídica |
| Frontend | `DocumentosAPI`, gestor, listado, selector, expediente y seguimiento requieren contexto/capacidades; nuevos diálogos distinguen “desvincular aquí” de “baja global”. Actualizar invalidación de cache al cambiar contexto, sesión/asignación/política; API protege incluso con HTML/JS antiguo |
| Descarga | Cada ID versión requiere autorización de manifest/contexto. Mantener attachment, octet-stream, nosniff, private/no-store de SS-06 y flujo de ruta vigente; TOCTOU SS-12 se trata por separado |
| Observabilidad | Auditoría funcional de decisión con IDs, actor, ámbito, versión y política. Diagnósticos SS-10 sólo códigos/correlación, sin nombres, texto de evidencia, rutas físicas o datos de otro expediente |

Un endpoint de capacidades podría ayudar a la UI, pero no sustituye la reautorización por operación y no debe revelar número/nombres de proyectos no legibles. Las rutas nuevas, códigos públicos y esquemas concretos se diseñan una vez aprobada la política; no hay cambio de API efectivo en esta entrega.

## Esquema y migraciones potenciales

No se crea SQL ni se modifica ninguna migración. La numeración futura debe elegirse contra la cadena canónica vigente cuando se autorice; no reservar arbitrariamente un número.

| Modelo | Cambios de datos potencialmente necesarios |
|---|---|
| A | Si sólo se endurece escritura, puede empezar con resolución completa de alcance sin modificar versiones. Persistir consentimiento, pertenencia estable y permisos administrativos explícitos requiere relaciones/política adicionales; no usar descripción o tipo_documento como bandera |
| B | Nueva unidad documento-expediente y manifest de versiones; relación de derivación con documento/versión de origen; metadatos locales; transición de referencias. No mover versiones existentes mediante UPDATE: el trigger las hace inmutables |
| C recomendado | Política documental versionada con estado privado/compartido/legado-en-revisión; ámbito propietario estable; participantes y sus estados/decisiones; manifest participante-versión; anotaciones locales y referencia de evidencia fijada opcional aprobada |

Para C, propuesta relacional conceptual (nombres no definitivos):

- Política por D con versión de decisión, modalidad, ámbito propietario, actor/fecha/motivo protegido; historial de cambios, no sobrescritura sin traza.
- Participación con clave estable a un ámbito canónico, estado activo/suspendido/retirado y decisión de consentimiento; FK a D y ámbito. Relacionar participantes y destinos de DocumentoVinculo sin reescribir la historia de vínculos anteriores.
- Publicación de versión por participante/ámbito y decisión. Garantizar que la versión pertenece al mismo D mediante claves compuestas o validación equivalente verificable, no una FK independiente que acepte una versión ajena. Estados/retiros auditables; no editar DocumentoVersion.
- Relación opcional de evidencia/manifiesto en requisitos/seguimiento, manteniendo referencia global histórica y procedencia. La política jurídica de fijación tiene que aprobarse antes del backfill.
- Índices para D/participante/versión y ámbito activo, unicidad coherente y restricciones de estado, sin duplicar las de hash/ruta/número ni el índice único de vínculo activo ya existentes.

Preferir ámbitos respaldados por FKs verificables frente a pares tipo/id sin integridad; si se mantienen destinos polimórficos, especificar validación de pertenencia y ciclo de vida para cada tipo. Un objetivo núcleo→varios proyectos no crea participantes automáticamente. RLS puede evaluarse como defensa adicional, pero no se presume presente ni se diseña un parche aislado a `app.current_user_id` en SS-05.

La estrategia de migración debe ser forward-only, aditiva y probada en clon QA: conservar originales, IDs, SHA, nombres y fechas; primero registrar equivalencias y decisiones pendientes, luego revisarlas. No alterar el baseline001/027/028, desactivar triggers inmutables, eliminar vínculos, mover archivos o cambiar estados jurídicos. Una copia/derivado necesita nueva identidad y procedencia autorizada; deduplicación física futura no concede acceso ni debe exponer igualdad de hashes a otros expedientes.

## Coordinación transaccional y SS-12

Diseñar un protocolo común para cambios globales, publicación, vínculos, participantes y asignaciones. Un lock sólo en Documento no serializa automáticamente la revocación de UsuarioProyecto, nuevos vínculos o cambios de ascendencia si esos escritores no cooperan. Definir orden global compatible con auditoría/catálogos/FKs y SS-12; documentos múltiples por ID ordenado, evaluación de ámbito y membresías coherente, lectura de autorización nuevamente antes de confirmar. No añadir ahora `FOR UPDATE` a una consulta con relaciones cargadas ni mutex por proceso.

Los [bloqueos de PostgreSQL15](https://www.postgresql.org/docs/15/explicit-locking.html) se mantienen normalmente hasta el fin de la transacción; coordinar todos los escritores y probar deadlocks/rollback es necesario. Con [Read Committed](https://www.postgresql.org/docs/15/transaction-iso.html), consultas sucesivas pueden ver cambios confirmados: un chequeo de autorización temprano no asegura el estado al commit. Diseñar y validar el aislamiento, snapshots, locks o revisiones de política; no prometer una revocación simultánea absoluta sin definir su punto de ordenación.

No mantener locks mientras un humano decide compartir ni durante una transferencia larga sin un diseño operativo justificado. Usar decisiones/solicitudes persistidas y una transacción corta final; cancelación y trabajo documental siguen el diseño SS-12. La publicación exclusiva/limpieza conservadora existente no da atomicidad con PostgreSQL y no debe perderse al añadir autorización.

## Plan incremental y puertas de avance

| Fase futura | Resultado revisable | Condición de avance |
|---|---|---|
| 0 actual | Tres documentos, matrices actual/propuesta y 38 comprobaciones puras de código actual | Entrega de diagnóstico; detenerse, sin cambios de permisos |
| 1 decisión | D01–D12 y matriz firmadas funcionalmente; casos legítimos y restringidos definidos | Aprobación expresa de la política; también de excepciones/legado |
| 2 contrato | Especificación de API contextual y migración/consumidores, protocolo de concurrencia y modelo de datos | Revisión AppSec, documental, backend/frontend; autorización independiente para implementación/migraciones |
| 3 implementación aislada | Helpers puros, contratos y pruebas negativas con dobles; sin corte institucional | Pruebas de política y regresión previas pasan; no confundir con SQL real |
| 4 QA integrado | BD PostgreSQL desechable autorizada, storage sintético, API/Starlette real y navegador local con red institucional bloqueada | Evidencia de matriz completa, concurrencia, respuestas, migración/restauración y SS-06/12 |
| 5 ensayo de legado | Inventario QA, clasificación/resolución por responsable, comparación de referencias y manifests, simulación del corte | Cero reclasificaciones/ACL inferidas sin decisión; plan de continuidad/rollback aprobado |
| 6 revisión de integración | Diff final y evidencia QA; evaluación del despliegue como tarea separada | Nueva autorización; no incluida en esta fase |

Mantener la política antigua durante un ensayo no debe crear rutas alternativas después del corte. El modo comparativo de decisiones sólo se ensaya con datos sintéticos y resultados controlados; no vuelca expedientes ni denegaciones sensibles a logs. Los documentos legados sin resolución son un bloqueo explícito del corte o una excepción de continuidad con riesgo aceptado y fecha de revisión, nunca una clasificación automática como “compartido público”.

## Diseño de pruebas sintéticas

Fixture propuesto: proyectos PA/PB/PC activos; PN-A y PN-B con núcleos distintos y un segundo caso con núcleo compartido; operadores Oa, Ob, Oab, O0; admin, visualizador y geógrafo; D con LA/LB y V1/V2, V1 anterior a LB; referencias de requisito y seguimiento en A/B. Tokens/datos sintéticos únicamente. En C, Q(A,D)={V1}, Q(B,D)={V2}; V3 sin publicar; participante B suspendido y un vínculo histórico inactivo. Para B crear unidades separadas; para A aprobar deliberadamente todo el histórico.

`P` = prueba pura con dobles/objetos y funciones sin engine; `Q` = PostgreSQL QA desechable autorizada con API real; `N` = navegador local con backend QA sintético. **Todas las pruebas siguientes son propuestas; sólo la corroboración actual de 38 ramas se ejecutó en fase0.**

| ID | Casos positivos y negativos / resultado esperado | Nivel necesario |
|---|---|---|
| T01 | M,V,Dv,G,L+,BG,U,Cn cruzados con cuatro roles y alcances de la matriz. Actual conserva semántica registrada; propuesta deniega modificación global sólo A/B | P exhaustiva y Q HTTP. Roles sin alcance hipotético marcados contrafactuales, no resultado del producto |
| T02 | Metadatos globales compartibles visibles; notas locales y procedencias exclusivas B ausentes desde A; probar serialización completa incluidos campos AuditRead | P esquemas; Q consultas/respuestas |
| T03 | V1/V2 actuales legibles por cualquier vínculo; C permite sólo Q del contexto. Probar lista, descarga directa, URL antigua, IDs adivinados y contexto falsificado | P decisiones; Q API/Starlette y bytes sintéticos |
| T04 | V1 anterior a LB sólo se publica a B por aprobación expresa; V3 futura no aparece automáticamente ni en nombres, tamaños, hashes, conteos o consolidado | P manifest; Q consultas/versionado |
| T05 | Operador sólo A/B no cambia metadatos ni sube versión global C; Oab sí con Pguard completo; lector/geógrafo no capturan; admin usa facultad explícita | P; Q persistencia, auditoría y rechazo sin efectos |
| T06 | L+ exige fuente, destino, conjunto previo y decisión; destino sólo B rechazado para Oa. Un vínculo a núcleo común expande A+B y no se autoriza por primer proyecto | P resolución simulada; Q todas ramas canónicas |
| T07 | U sólo LA exclusivo autorizado; LB y D conservados. Último vínculo, referencias pendientes, vínculo común A+B y retiro sin autorización rechazados/controlados | P; Q unicidad, estados, FK y auditoría |
| T08 | BG operador incluso A+B rechazada en C; admin con motivo autorizado cierra todo sin borrar versiones/bytes. Historia administrativa separada no abierta a operadores | P; Q transacción/auditoría/descarga posterior |
| T09 | LA/LB inactivos, ambos inactivos, D inactivo, padres/proyecto inactivos, objetivo inválido y Pguard desconocido; no acceso por conjunto vacío ni por retiro silencioso | P; Q SQL y códigos acordados |
| T10 | Consolidado A/B conserva sólo sus procedencias; referencia sola no concede archivo; C latest aprobado por contexto, sin pérdida de categorías individual/colectivo | P contrato; Q SQL y N agrupación |
| T11 | Reasignación A→B, revocación total, alta nueva, sesión vigente y cache previa; nueva solicitud no hereda permisos antiguos ni Q ajeno | P snapshots; Q sesiones reales de QA y N |
| T12 | Dos conexiones: upload vs alta/desvinculación, BG vs descarga, revocación/asignación vs modificación, suspensión de proyecto vs captura. Barreras en chequeo/commit; verificar punto de ordenación acordado y no deadlock/retry infinito | Sólo Q demuestra locks/MVCC; P no basta |
| T13 | Referencia a D ajeno, inactivo o versión de otro D; conservar referencias antiguas, no conceder lectura. Derivado autorizado conserva origen sin revelar el original a quien no tiene permiso | P; Q FK/constraints/serialización |
| T14 | Migración aditiva en clon: recuentos, IDs, SHA/bytes, versiones inmutables y estados jurídicos idénticos; sin UPDATE/DELETE de versiones ni pérdida de procedencia | Q con snapshot/restore sintético, no institucional |
| T15 | UI de gestor/listado, vínculos, baja/desvinculación, historial, ver/descargar, seguimiento individual/colectivo y requisitos; enlaces directos con frontend antiguo siguen protegidos por API | N + Q, no basta ocultar botones |
| T16 | Regresión SS-06/SS-12: MIME canónico, validación formatos, attachment/octet-stream/nosniff/no-store, SHA/bytes, publicación exclusiva, cancelación/commit incierto sin borrar archivo ajeno | P existentes y Q nativa; TOCTOU no se declara cerrado |
| T17 | Decisión y motivo en auditoría protegida; logs finales sólo código/correlación; ni nombres de otro expediente ni tokens/query/paths sensibles | P formateo SS-10 y Q eventos funcionales |
| T18 | Paginación/presupuestos de nuevas consultas, duplicados por múltiples procedencias y respuesta vacía. No introducir carga N+1 o materialización sin límites al resolver manifests | P construcción; Q planes/datasets sintéticos acotados, sin estrés institucional |

Las pruebas de actual y propuesta tienen oráculos separados: un test que hoy permite baja global por A no debe presentarse como prueba de aceptación de C. El test futuro debe esperar denegación y ausencia de cambios B. En QA, probar ambos órdenes de operaciones concurrentes y varios procesos; un mock no reproduce aislamiento ni permisos del servidor.

## Pruebas existentes aprovechables, no ejecutadas en esta fase

| Fuente | Cobertura inspeccionada | Vacío para SS-05 |
|---|---|---|
| `backend/tests/test_auth_rbac.py` | Sesión/CSRF y filtro por proyectos | No prueba lectura/escritura global de D multivínculo |
| `backend/tests/test_document_targets_039.py` | Tipos canónicos, objetivos inexistentes/no autorizados/inactivos, roles, vínculo existente, versiones y requisitos | Ampliar a matriz de dos proyectos, consentimientos, manifest y carreras |
| `backend/tests/test_documents_dashboard.py` | Versiones inmutables/descargables y agregación | Separar vigencia contextual y autorización de V1/V2 |
| `backend/tests/test_frontend_read_models.py:47–159` | Consolidación de procedencias, máximo global, exclusión de otro PN y vínculos inactivos, roles. El caso núcleo compartido es especialmente relevante | Nueva semántica contextual requiere nuevos oráculos y aprobación; no conservar max global por accidente |
| AIS-03, cobertura de auditoría | Funciones reales aisladas confirmaron permiso/baja global | No acredita autorización HTTP, SQL o una política institucional |
| `tests/security/test_document_validation.py`, `test_document_storage.py`, `test_document_starlette_pending.py` | SS-06, almacenamiento SS-12 y casos nativos pendientes | Algunas decisiones de acceso están dobladas; no equivalen a RBAC integrado |
| `tests/qa/test_document_publication_postgresql.py` | Protocolo SQL/publicación preparado en SS-12 | No es el servicio real ni la política SS-05; ampliar tras aprobación, sin ejecutarlo ahora |

No lanzar suites backend ni `--collect-only` sin confirmar aislamiento y autorización. QA requiere host/puerto/BD explícitos de clon desechable, identidad sintética y privilegios mínimos, configuración de uploads temporal propia, conectividad institucional bloqueada y revisión de fixtures antes de ejecutar. `conftest` y un nombre de BD son controles auxiliares, no prueba de autorización o aislamiento efectivo.

## Criterios de aceptación para una futura implementación

1. Política D01–D12 aprobada, cada celda y excepción trazable a esa aprobación; ninguna regla jurídica inferida por AppSec.
2. Operador sólo A no modifica ni da baja evidencia global que afecta B, según el modelo aprobado; tampoco amplía destinatarios con un objetivo compartido implícito.
3. Lectura de versión determinada por política aprobada, incluida historia previa al vínculo y futuras altas; ID directo o endpoint antiguo no elude autorización.
4. Consolidado y frontend respetan el mismo contexto; no exponen procedencias/notes fuera de alcance; “vigente” tiene significado explícito y probado.
5. Desvinculación local preserva otros expedientes, versiones, archivos y referencias históricas; baja global es una acción distinta y auditada.
6. Asignaciones/proyectos inactivos y cambios concurrentes no producen permisos por omisión; QA demuestra el protocolo y sus límites de revocación.
7. SHA, bytes, IDs históricos, metadatos SS-06 y garantías locales SS-12 conservados; migración forward-only ensayada y revisión/restauración autorizadas.
8. Matriz completa pasa en API/PostgreSQL QA y navegador local, con resultados y omisiones separados; no declarar garantías de mocks como integradas.
9. Legado clasificado por decisión expresa o excepción de continuidad aceptada; sin borrado, backfill jurídico o compartición masiva implícitos.
10. Evaluación final de riesgos residuales y revisión técnica antes de cualquier integración o despliegue, que quedan fuera de esta autorización.

## Entrega de fase0 y control de cambios

Se crearon exclusivamente estos tres documentos, sin sobreescribir otros:

- `docs/security/SS-05-ANALISIS-POLITICA-DOCUMENTAL-2026-10-28.md`.
- `docs/security/SS-05-MATRIZ-DECISION-RBAC-2026-10-28.md`.
- `docs/security/SS-05-PLAN-IMPLEMENTACION-2026-10-28.md`.

Se verificaron hashes contra un snapshot inicial de719 archivos preexistentes (excluyendo `.env`), enlaces relativos de los documentos y `git diff --check`. El apéndice de análisis se ejecutó:38 comprobaciones puras aprobadas. No se ejecutaron suites integradas, PostgreSQL, Docker, migraciones, scripts operativos o herramientas nuevas; no hubo commit/push/merge/despliegue.

**Fase0 terminada: detenerse tras entregar el análisis. No implementar SS-05 hasta aprobación funcional expresa.**
