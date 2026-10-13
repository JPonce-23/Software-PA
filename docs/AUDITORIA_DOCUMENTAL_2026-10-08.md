# Auditoría documental de SOFTWARE-PA — 2026-10-08

## Alcance y fuentes

Actualización exclusivamente documental sobre el estado local del backend,
conservando los cambios previos B-07 y las proyecciones de lectura. No se
inspeccionó el frontend ni se ejecutaron escrituras en la base de datos.

Se contrastaron `backend/app/models.py`, `schemas.py`, `main.py`, routers de
dominio, documentos, GIS y reporting, los servicios de acceso, dominio,
conciliación, historia y read-models, las migraciones canónicas 001–028 y
OpenAPI generado mediante `app.openapi()`. También se consultaron metadatos
de columnas en `software_pa_test` (esquema aplicado 028), sin datos operativos.
El ledger de la base predeterminada de Compose registra 006: el linaje canónico
no equivale al esquema aplicado en todas las bases. `/health` informa este último.
No se intentó actualizar ninguna base.

Documentos existentes auditados:

| Archivo | Resultado de esta auditoría |
|---|---|
| [API.md](API.md) | Correcciones de descripciones; esquema 028, B-07 y §11 de read-models ya estaban documentados correctamente. |
| [ARQUITECTURA.md](ARQUITECTURA.md) | Esquema, infraestructura, relaciones, seguridad, seguimiento y proyecciones actualizados. |
| [DICCIONARIO_DATOS.md](DICCIONARIO_DATOS.md) | Campos, tablas de pertenencia, tipos, nulabilidad, referencias API y distinción GIS histórica/vigente corregidos. |
| [MIGRACIONES.md](MIGRACIONES.md) | Inventario 001–028 y hashes verificados; contrato DDV original aclarado como histórico. |
| [MODELO_FUNCIONAL.md](MODELO_FUNCIONAL.md) | Descripciones de la implementación existente alineadas con 016, 008 y schemas; principios Excel-First preservados. |
| [FUENTES_Y_COBERTURA_EXCEL.md](FUENTES_Y_COBERTURA_EXCEL.md) | Cobertura de indemnización en ambos ámbitos y correspondencia de campos/rutas corregidas. |
| [README.md](README.md) | Índice, linaje vigente y separación de informes históricos corregidos. |
| [../README.md](../README.md) | Servicio scheduler inexistente retirado del inventario y comandos documentados. |
| [../backend/db/seeds/README.md](../backend/db/seeds/README.md) | Baseline 001 como prerrequisito, sin afirmar que deba ser el máximo aplicado. |
| [../backend/db/fixtures/README.md](../backend/db/fixtures/README.md) | Revisado; sin cambios. |
| [DERECHOS_COLECTIVOS_PARA_FRONTEND.md](DERECHOS_COLECTIVOS_PARA_FRONTEND.md) | Corte original aclarado; añadido el read-model documental actual. No se revisó código del cliente. |
| [INFORME_DERECHOS_COLECTIVOS_2026-10-02.md](INFORME_DERECHOS_COLECTIVOS_2026-10-02.md) | Conservado con aviso de alcance histórico. |
| [INFORME_CONCILIACION_GIS_2026-10-05.md](INFORME_CONCILIACION_GIS_2026-10-05.md) | Conservado con aviso de etapa previa a 026 y B-07. |
| [INFORME_AUDITORIA_HISTORIA_GIS_2026-10-05.md](INFORME_AUDITORIA_HISTORIA_GIS_2026-10-05.md) | Bloqueo y diseño original conservados; no presentados como límites actuales. |
| [INFORME_ESTABILIZACION_LINAJE_GIS_2026-10-05.md](INFORME_ESTABILIZACION_LINAJE_GIS_2026-10-05.md) | Corte 001–025 conservado; no presentado como máximo actual. |
| [QA_AUDITORIA_HEARTBEAT_020.md](QA_AUDITORIA_HEARTBEAT_020.md) | Evidencia y resultados conservados con fecha/alcance histórico. |
| [QA_ASIGNACIONES_PROYECTO.md](QA_ASIGNACIONES_PROYECTO.md) | Evidencia y resultados conservados con fecha/alcance histórico. |
| [openapi.json](openapi.json) | Comparado con la aplicación; idéntico, sin modificación. |

La única edición Python de esta auditoría es el docstring inicial de
`backend/tests/test_gis_history_regressions.py`: la referencia a 024 se sustituye
por el linaje canónico 025–026. Usuario ya estaba documentado como parte de
baseline 001; no se encontró una referencia vigente a migración 031 que requiriera
otra edición. No se alteraron cuerpos de funciones, clases, imports ni pruebas.

## Discrepancias y clasificación

| Hallazgo | Clasificación y resolución |
|---|---|
| Esquema 015 en arquitectura/índice y validación 001–025 en diccionario | Documentación obsoleta: ahora 001–028. API.md ya indicaba 028 al comenzar esta auditoría. |
| Referencias GIS de 025 sin mencionar historia 026 | Documentación incompleta: vigente `conciliacion-v3-historia`; `conciliacion-v2` conservado como histórico de 025. |
| Informes que aún parecían afirmar que no existían ciclos/revisiones o que 025 era el máximo | Referencia histórica válida: se añadió alcance explícito, sin reescribir sus resultados. |
| B-07 y mapa | Revalidado contra reporting.py; documentación actual ya refleja precedencia de geometrías activas/vigentes por proyecto, fallback global legacy, parcelas por pertenencia administrativa, DDV poligonal separado y `trazo_proyecto` independiente. |
| Actores, destinos, documentos y totales | Revalidado: son read-models, no entidades ni reglas nuevas. Se añadieron referencias desde arquitectura y guía documental colectiva. |
| `fecha_fin_estimada`, `Afectacion.id_parcela`, campos documentales atribuidos a ParcelaTitular, `Indemnizacion.monto_total` | Contradicción documental: se describen los campos reales, la relación indirecta hacia Parcela y la ubicación real de certificados/folios; se retira el campo inexistente de indemnización. |
| Tipos/nulabilidad y claves N:M incorrectos | Documentación obsoleta: corregida contra modelo, SQL canónico y catálogo de columnas. Las parejas activas son únicas y tienen PK propia, no PK compuesta. |
| Referencias de DocumentoVersion | Documentación obsoleta: `id_documento_version` y `hash_sha256`. |
| Ruta inexistente de actividades, requisitos con `id_requisito_documental`/`estado`, FIFONAFE con `fecha_solicitud`/`resultado` | Contradicción documental: rutas y nombres actuales, `id_requisito`, `id_estado`, fechas existentes y `resultado_no_conflictos`. |
| Asamblea descrita con campos opcionales como obligatorios; referencia/observaciones de Pago obligatorias | Documentación obsoleta: requisitos de entrada alineados con los schemas vigentes, sin modificar validadores. |
| Cuatro oficios como criterio general de completitud FIFONAFE | Contradicción documental: legado v1 separado de acreditación integral v2 ya implementada en 008 y sus hitos. |
| SeguimientoEvento descrito como tabla append-only | Contradicción documental: admite edición y baja lógica; la bitácora es la historia inmutable de esas mutaciones. |
| Bitácora con INSERT directo para aplicación, aislamiento documental como prohibición general de compartir entre proyectos | Contradicción documental: se describen SELECT runtime/INSERT por trigger y autorización independiente al documento y objetivo. |
| CSRF sin excepción de login y errores 404 para alcance no autorizado | Documentación obsoleta: excepción de origen en login y convención 403 por alcance conservadas como están implementadas. |
| Scheduler, vistas materializadas y ubicación de DATABASE_URL | Documentación obsoleta: cuatro servicios base, vistas SQL normales y configuración real. |
| Unidad siempre en hectáreas sin distinguir áreas GIS | Ambigüedad documental: hectáreas administrativas separadas de métricas GIS en m². ST_Area nunca proporciona superficie oficial. |

## Read-models verificados

- Actores GIS: `creado_por_nombre`, `usuario_nombre` y
  `usuario_revision_nombre` opcionales, manteniendo los IDs. Sólo nombre completo
  actual; sin correo, rol, número de empleado o información laboral.
- Revisiones: `destino` opcional con núcleo, municipio, entidad y número de parcela
  derivados mediante consultas en bloque. Matching e identidad no cambian.
- Candidatos: etiquetas del snapshot existente `universo_destinos`, sin nuevas
  copias por candidato ni consulta por cada fila.
- `GET /api/proyecto-nucleo/{id_proyecto_nucleo}/documentos`: procedencia por
  vínculo/referencia autorizada, `entidad_tipo`, `entidad_id`, `origen`, datos de
  Documento y versión de máximo `numero_version`; no publica procedencias ajenas
  al expediente, respetando los objetivos compartidos del núcleo existentes.
- `X-Total-Count`: GET de importaciones del proyecto, features, conciliaciones y
  revisiones GIS. Misma consulta filtrada antes de `skip/limit`, array conservado
  y header expuesto en CORS a los orígenes permitidos.

## Evidencia Excel revalidada

Lectura local de XML dentro de XLSX, incluyendo strings compartidos y ubicación
real de las hojas. Sólo se incorpora evidencia de encabezados/estatus y
coordenadas de celdas a esta documentación; los libros no se versionan.
La comprobación se acotó a encabezados y estatus de indemnización; no reaudita
todo el contenido de los libros ni establece equivalencias de montos o fechas.

| Libro operativo local | SHA-256 |
|---|---|
| `Copia SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS MQ_COLECTIVOS MEET 27082026.xlsx` | `38092fafed5e9fd3dac58178ad5714754537bb69b4be03ee5f26c3ece57d9fc1` |
| `Copia de SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS (REV) MQ.xlsx` | `a48cd3d94f9ed67671810550f9cd1eec33961bfc438edcda7af6976b40da325d` |
| `SEGUIMIENTO DE ACTIVIDADES LIBERACIÓN DE VIAS-INDIVIDUALES-MQ.xlsx` | `96ea82d1e4ff98fab63e27eea1a8bd0936b2aed70724e4b024fa5d5f2056f495` |

Los encabezados/celdas se detallan en
[FUENTES_Y_COBERTURA_EXCEL.md §3.4](FUENTES_Y_COBERTURA_EXCEL.md#34-indemnización-colectiva-e-individual-evidencia-revalidada).
El significado común de estatus y entrega está acreditado en colectivo e
individual. `PAGADO` aparece literalmente en ambos; el modelo ya admite `pagado`
desde 002. Se actualiza sólo cobertura, sin ingesta ni cambios de datos.

## Historia conservada y límites pendientes

Se conservan las referencias a 027 como migración de actividad documental, a
025/`conciliacion-v2` como contrato histórico, las numeraciones GIS anteriores a
la estabilización y los HEAD, bases, resultados y conteos de informes fechados.
El test de backfill mantiene sus fixtures v2 porque comprueba historia 025→026.
El reconciliador excepcional mantiene su inventario congelado 001–025; ese
contrato específico no es una referencia obsoleta al máximo de la aplicación.

No se infieren fecha de resolución/pago, monto resuelto, beneficiario o Pago
efectivo desde el estatus `PAGADO`. La revisión acotada no acredita una equivalencia
entre un supuesto monto resuelto independiente y los importes de avalúo,
convenio o pago; no se establece un nuevo mapeo ni se inventa un campo.
Las decisiones preexistentes sobre `VALIDACIÓN PA/SICT` y `2A_ADICIONAL`
permanecen como estaban documentadas, sin resolverlas automáticamente.

Al contrastar metadatos, el ORM declara nullable algunos campos que el SQL físico
restringe (por ejemplo, órgano/cargo/calidad de OrvIntegrante). El diccionario
conserva la restricción SQL NOT NULL verificada; no se corrige el ORM en una
auditoría exclusivamente documental.

## Verificación y preservación

Resultados de los controles documentales:

- `docs/openapi.json` coincide byte por byte y como JSON con OpenAPI generado
  desde la aplicación actual, también en la comprobación final: 136 rutas y
  171 schemas. Se conserva sin regenerarlo en el repositorio.
- SHA-256 de ambas especificaciones:
  `d4d606478daa81468b12cbe835fb0868830fa49430f669e8e31218fc33a49cc5`.
- Los 28 checksums de MIGRACIONES.md coinciden con los SQL canónicos.
  Los 28 archivos de migración mantienen sus bytes iniciales; ninguno fue creado,
  eliminado o modificado.
- Se contrastaron 153 columnas simples de las tablas del diccionario contra
  tipos del modelo y nulabilidad SQL; las filas corregidas no tienen discrepancias.
- El inventario inicial de 201 archivos backend/docs y la copia de textos antes
  de editar permiten separar este diff del trabajo previo. Los archivos
  funcionales Python mantienen sus bytes; el único Python editado conserva su
  AST ejecutable tras excluir docstrings.
- El diff completo de esta auditoría contiene sólo Markdown y el docstring
  indicado. El único archivo nuevo es este informe documental.
- `git diff --check`: correcto, sin errores, en la verificación final.

No se ejecutan pruebas funcionales ni contratos SQL con fixtures: esta entrega
no cambia comportamiento y no debe modificar datos. Las pruebas citadas en
informes históricos conservan sus fechas y resultados originales.

No hubo cambios funcionales, endpoints, schemas, migraciones, tablas, columnas,
constraints, datos, permisos, matching/conciliación GIS ni reglas Excel-First.
No hubo commit, push, merge, reset o deploy. B-07 y las mejoras de read-model
preexistentes se conservan.
