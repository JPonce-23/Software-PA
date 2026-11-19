# PR #8: conciliación local con dev — 19/11/2026

Directorio autorizado: `/home/alfredo/proyectos/Software-PA-preflight-qa`.
Rama: `security/integracion-pa5-final-20261118`. Estado inicial limpio.
HEAD inicial y remoto de #8: `ae9cd6021b15d45f4091ab9854d394348cacfbc0`.
Base común: `b38ec384009f36ccc2be93ac9ee375d51f16845f`.
Dev incorporado: `c1b4a00317c4915d0ae4a77e37de4c1b1af09f92`, comprobado por fetch y lectura remota posterior.

La integración se prepara con `git merge --no-commit --no-ff origin/dev`, se prueba y después se confirma localmente. No se reescribe historial ni se fusiona la rama de destino. El SHA final, padres, diff y logs se registran después del commit en `outputs/pr8-integration-20261119/INFORME-FINAL.md` (expediente local ignorado por Git).

## Cambios del equipo preservados

Dev aporta un commit: «Facilitar la consulta del resumen con filtros, colores e íconos centrados».
Se conservan íntegros `backend/app/routers/reporting.py`, `backend/app/services/project_overview.py`, `frontend-ssalfer/js/seguimientoFifonafe.js`, `frontend-ssalfer/styles/dashboard.css` y `frontend-ssalfer/styles/resumenProyecto.css` respecto de ese commit.
El endpoint `/proyectos/{id_proyecto}/resumen-ampliado/origenes` conserva autorización por proyecto, roles, siete tipos de consulta, paginación y límites. El resumen mantiene sus enlaces de origen, estados de actividades/pagos y filtros individual/colectivo de FIFONAFE.

`frontend-ssalfer/dashboard.html` fue el único archivo modificado por ambas ramas. No hubo conflicto textual: se conserva la fecha de actualización de dev y la referencia de #8 a `exceljs-4.4.0-ssalfer.min.js`. No se restauró el bundle anterior.

## Correcciones justificadas por las pruebas

- La huella del dashboard y dos referencias a su CSS en los inventarios SS-08/SS-09 se actualizan a los bytes revisados. No se regeneran otras evidencias ni se cambian políticas CSP, migraciones o contratos de seguridad.
- Una prueba CSP recorría HTML ignorado de herramientas `node_modules`, ajeno a la imagen publicada. Se limita a los mismos HTML raíz y `pages/` publicados por el Dockerfile y se agrega una regresión que incluye páginas anidadas y excluye herramientas. No se añaden hashes de dependencias de compilación a las políticas.
- Una nueva prueba reprodujo una carrera del diálogo del resumen: cerrar una consulta y abrir otra permitía que la respuesta anterior sobrescribiera la nueva selección. Se agrega un identificador de consulta para rechazar respuestas y errores obsoletos, manteniendo las funciones nuevas de dev.
- Se agregan ocho regresiones backend: consultas reales SQLAlchemy en SQLite en memoria con modelos reales, conteos, aislamiento de proyecto, inactivos, pagos sin duplicación, asambleas, actividades, paginación superior a 200 y autorización/validación HTTP. Se bloquean conexiones PostgreSQL.
- Se agregan siete pruebas Node ejecutando los callbacks reales en VM con DOM/API sintéticos: destinos, paginación, escape, estados, errores, carrera, cambio de proyecto y filtro inicial FIFONAFE. No son pruebas de navegador ni mediciones de render.

## Validación realmente ejecutada

| Grupo | Aprobadas | Fallidas finales | Omitidas |
| --- | ---: | ---: | ---: |
| 33 suites Python de seguridad, cada una en intérprete separado | 627 | 0 | 0 |
| SSALFER Node, suite completa | 154 | 0 | 0 |
| Linaje de migraciones, pytest sin conftest y PostgreSQL bloqueado | 15 | 0 | 23 |
| Total de pruebas | 796 | 0 | 23 |

Dentro de seguridad: SS-07 incluye 23 pruebas de auditoría/gramática; suministro +pa5 incluye 23 contratos offline; runner de migraciones incluye 30 pruebas con psql sintético. No sumar nuevamente esos subconjuntos al total.

Comprobaciones adicionales: parser PostgreSQL sobre las 34 migraciones, con igualdad byte a byte respecto de ambos padres; AST de 218 archivos Python; sintaxis shell/JavaScript/YAML y bloques run; permisos/pins de Actions oficiales; workflows idénticos al HEAD inicial; `git diff --check`; `pip check`; SS-09 cadena local; dos páginas protegidas y 102 registros de recursos; ExcelJS (78 paquetes, 337 módulos) y SheetJS (dos archivos iguales a distribución oficial fijada por SHA-256).

La primera pasada de seguridad registró tres fallos y un error por las huellas obsoletas y el alcance CSP; la nueva regresión Node registró un fallo por la carrera. Se conservan los logs iniciales. Las suites afectadas se repitieron tras corregirlos y aprobaron; las demás conservan su ejecución aprobada. No se presenta el resultado inicial como verde.

Entorno local: Python 3.12.3 y Node 22.23.2. Dependencias exactas de backend y herramientas CI instaladas en `.venv` privada de este worktree; `pip check` sin incompatibilidades. Python 3.11.17 del workflow aún necesita la ejecución remota correspondiente. El entorno original no traía pip/ensurepip; se usó una herramienta pip temporal desde PyPA con hash registrado en el expediente. No se instalaron paquetes del sistema.

Las 23 pruebas omitidas de linaje escriben en una instancia PostgreSQL desechable marcada y requieren su activación expresa. No se activó esa instancia. Tampoco se ejecutó la suite backend completa contra PostgreSQL/PostGIS, las campañas nativas de GDAL/PostGIS, pruebas de navegador, ni las QA opt-in que escriben en bases. Las ocho regresiones backend SQLite/HTTP no sustituyen esas verificaciones.

## Excepciones y criterio de integración

Las verificaciones locales soportan actualizar el PR #8 para revisión de integración de código en dev. **No sustentan un merge incondicional ni aprobación de producción.** La descripción remota vigente de #8 exige publicación/consumo nativo antes de merge. Para integrar sin GHCR inmediato, el propietario debe aceptar explícitamente una excepción acotada a desarrollo, documentarla en #8 y verificar que no contradiga las protecciones/checks requeridos de la rama. El agente no concede esa excepción ni cambia permisos o reglas.

La excepción debe mantener pendientes, sin marcarlos PASS:

1. Suministro real del artefacto +pa5 a un runner independiente, importación del Engine, ABI/componentes y smoke PostgreSQL/PostGIS/GDAL, con logs verificables. Los 23 gates F2-E1 son evidencia histórica y no se repitieron aquí.
2. Decisión del propietario sobre distribución pública/privada del archivo Docker. No se modifica el mecanismo ni se publica una Release.
3. Publicación GHCR privada autorizada y pull por digest en otro runner, permisos de lectura y procedencia efectiva. Ningún digest local demuestra existencia remota.
4. Conciliación posterior con #9: añadir etiquetas OCI allí cambia config/manifiesto y deja igual el rootfs; el catálogo estricto actual de #8 no acepta esa nueva identidad automáticamente. No basta con cambiar una variable de digest. Esa conciliación requerirá revisión y autorización separadas después de aprobar el candidato.
5. SCA/SBOM de componentes realmente instalados y evidencias nativas, revisión de vulnerabilidades y aceptación del riesgo. `pip check`, el grafo ExcelJS y los manifiestos locales no equivalen a SCA/SBOM completo.
6. CI remoto del nuevo HEAD, PostgreSQL/PostGIS desechable con migraciones y roles reales, navegador/CSP y preflight de despliegue antes de cualquier producción.

Compose continúa seleccionando el artefacto local congelado; los equipos que no lo tengan no obtendrán una instalación funcional por fusionar el código. El override remoto sólo puede activarse con una referencia inmutable aprobada y disponible. No cambiar a una imagen base pública o recompilada para ocultar la falta de suministro. Los jobs pendientes/omitidos no son aprobación. Sin aceptación explícita de la excepción y sin cumplir las reglas de rama, mantener #8 como draft y no fusionar.

Se conservan fuentes, parches, Dockerfiles, catálogos, verificadores y workflows +pa5; no se modifican migraciones ni el Engine, ni las bases existentes, ni los otros worktrees, ni la rama/publicador #9. El único efecto Git compartido solicitado es actualizar referencias remotas con fetch y avanzar la rama de integración con un commit local.

## Operación manual posterior

Tras revisar el commit, actualizar #8 con push normal de esta rama. El push sólo actualiza el PR; no equivale a aprobar su merge ni a publicar imágenes. El comando exacto, con SHA final y las restricciones anteriores, figura en el informe final local y en la entrega del agente. No se ejecutó push, merge hacia dev/main, publicación, cambio de permisos ni eliminación de worktrees.
